import numpy as np
import copy
import string
import globals
import mapTools
from Structure import Structure
from StructurePrototype import StructurePrototype
from materials import INVENTORYLOOKUP, INVENTORY, SOILS, PLANTS, TREES, AIR
from worldLoader import WorldSlice


class Node:

    def __init__(self,
                 x: int = 0, y: int = 0, z: int = 0,
                 parentStructure: Structure = None,
                 buildArea=(0, 0, 0, 0),
                 mapOfStructures=np.array([]),
                 facing: int = None,
                 nodeStructurePrototype: StructurePrototype = None,
                 rng=np.random.default_rng(),
                 baseLineHeightMap=np.array([]),
                 oceanFloorHeightMap=np.array([]),
                 worldSlice: WorldSlice = None
                 ):

        self.rng = rng
        self.buildArea = buildArea
        self.mapOfStructures = mapOfStructures
        self.worldSlice = worldSlice

        # Create structure instance.
        self.structure = Structure(
            structurePrototype=nodeStructurePrototype,
            x=x, y=y, z=z,
            rotation=Structure.ROTATE_NORTH if facing is None else facing
        )

        # Translate structure position depending on facing direction.
        if facing is not None and parentStructure is not None:
            self.structure.setPosition(
                *mapTools.getNextPosition(facing, parentStructure.getBox(), self.structure.getBox())
            )

        # Create cropped heightmap for the ground underneath the structure.
        self.baseLineHeightMap = baseLineHeightMap
        self.oceanFloorHeightMap = oceanFloorHeightMap
        self.localHeightMapBaseLine = mapTools.getCroppedGrid(
            grid=baseLineHeightMap,
            globalOrigin=buildArea[:2],
            globalCropOrigin=self.structure.getOriginInWorldSpace(),
            globalCropFarCorner=self.structure.getFarCornerInWorldSpace()
        )
        self.localHeightMapOceanFloor = mapTools.getCroppedGrid(
            grid=oceanFloorHeightMap,
            globalOrigin=buildArea[:2],
            globalCropOrigin=self.structure.getOriginInWorldSpace(),
            globalCropFarCorner=self.structure.getFarCornerInWorldSpace()
        )

        # Bind connectors list from structure's custom properties.
        self.connectors = []
        if 'connectors' in self.structure.customProperties:
            if isinstance(self.structure.customProperties['connectors'], list):
                self.connectors = self.structure.customProperties['connectors']
                # Shuffle connector order to encourage meandering behaviour.
                rng.shuffle(self.connectors)

        self.chosenPostProcessingSteps = []
        self.pickPostProcessingSteps()

    # Evaluate if the current structure is placable.
    def isPlacable(self):
        return self.getPlacementCost() is not None

    def getPlacementCost(self):
        if self.localHeightMapBaseLine.shape != (self.structure.getSizeX(), self.structure.getSizeZ()):
            return None

        # Prevent structure from burying itself underground
        if self.localHeightMapBaseLine.max() + self.structure.groundClearance > self.structure.y:
            return None

        # Check if space is not already occupied by another structure
        structureMapCropped = mapTools.getCroppedGrid(
            grid=self.mapOfStructures,
            globalOrigin=self.buildArea[:2],
            globalCropOrigin=self.structure.getOriginInWorldSpace(),
            globalCropFarCorner=self.structure.getFarCornerInWorldSpace()
        )
        if np.any(structureMapCropped > 0):
            return None

        # Calculate height difference
        elevationFromOceanFloor = (self.structure.y - self.localHeightMapOceanFloor.mean())**3

        materialCost = self.structure.prototype.cost

        postProcessingStepsCost = 0
        for step in self.chosenPostProcessingSteps:
            if step is None:
                continue
            if 'decorationStructure' in step:
                postProcessingStepsCost += step['decorationStructure'].prototype.cost

        placementCost = materialCost + elevationFromOceanFloor + postProcessingStepsCost
        if globals.constructionBudget - placementCost < 0:
            return None

        return placementCost

    def pickPostProcessingSteps(self):
        if isinstance(self.structure.customProperties.get('postProcessing'), list):
            for operations in self.structure.customProperties.get('postProcessing'):
                if 'pillars' in operations:
                    self.chosenPostProcessingSteps.append({
                        'pillars': operations['pillars']
                    })
                    continue
                if 'decorations' in operations:
                    self.chosenPostProcessingSteps.append(self._pickDecorations(operations['decorations']))
                    continue

    # Set map of structures to a constant to indicate something is already been built here.
    def _updateMapOfStructures(self, structure: Structure):
        localOrigin, localFarCorner = mapTools.getCrop(
            globalOrigin=self.buildArea[:2],
            globalCropOrigin=structure.getOriginInWorldSpace(),
            globalCropFarCorner=structure.getFarCornerInWorldSpace()
        )
        self.mapOfStructures[
            localOrigin[0]:localFarCorner[0],
            localOrigin[1]:localFarCorner[1]
        ] = 1

    # Run function for each post-processing step.
    def _doPostProcessing(self):
        for step in self.chosenPostProcessingSteps:
            if step is None:
                continue
            if 'pillars' in step:
                self._placePillars(step['pillars'])
                continue
            if 'decoration' in step:
                self._placeDecoration(step['decoration'], step['decorationStructure'])
                continue

    # Place pillars post-processing function.
    def _placePillars(self, pillars):
        nodePivot = self.structure.getHorizontalCenter()
        for pillar in pillars:
            pillarPosition = mapTools.rotatePointAroundOrigin(
                nodePivot,
                [
                    pillar['pos'][0],
                    self.structure.y - 1,
                    pillar['pos'][1]
                ],
                self.structure.rotation
            )
            groundLevel = self.localHeightMapOceanFloor[
                pillarPosition[0],
                pillarPosition[2]
            ]
            pillarPosition = np.add(pillarPosition, [self.structure.x, 0, self.structure.z])
            mapTools.fill(
                *pillarPosition,
                pillarPosition[0], groundLevel, pillarPosition[2],
                pillar.get('material')
            )
            # If pillar has a facing direction for a ladder defined, put a ladder on this face of the pillar.
            if pillar.get('ladder') is not None:
                ladderRotation = (self.structure.rotation + pillar.get('ladder')) % 4
                self._placeLadder(pillarPosition, ladderRotation, groundLevel)

    def _placeLadder(self, pillarPosition, ladderRotation, groundLevel):
        ladderPosition = mapTools.rotatePointAroundOrigin(
            pillarPosition,
            np.add(pillarPosition, [0, 0, -1]),
            ladderRotation
        )
        for ladderY in range(groundLevel, self.structure.y):
            mapTools.setBlock(
                ladderPosition[0], ladderY, ladderPosition[2],
                'ladder',
                {
                    'facing': Structure.ROTATIONS[ladderRotation]
                }
            )

    # Place decoration structures post-processing function.
    def _pickDecorations(self, decorations):
        # TODO pick decoration based on global requirements (eg. needs at least one access ladder)
        # For each list of decorations, pick only one.
        decoration = self.rng.choice(decorations)
        if decoration is None:
            return None

        # Pick random orientation for decoration or one of the pre-defined directions.
        facing = self.rng.integers(4)
        if isinstance(decoration.get('facing'), list):
            facing = self.rng.choice(decoration.get('facing'))

        decorationOrigin = [0, 0, 0]
        if isinstance(decoration.get('origin'), list) and len(decoration.get('origin')) == 3:
            decorationOrigin = decoration.get('origin')

        rotation = (facing + self.structure.rotation) % 4

        decorationStructure = Structure(
            structurePrototype=self.structure.prototype.decorationStructures[decoration.get('decorationStructure')],
            rotation=rotation,
            x=self.structure.x + decorationOrigin[0],
            y=self.structure.y + decorationOrigin[1],
            z=self.structure.z + decorationOrigin[2]
        )

        return {
            'decoration': decoration,
            'decorationStructure': decorationStructure
        }

    # Place decoration structures post-processing function.
    def _placeDecoration(self, decoration, decorationStructure):
        decorationOptions = decoration.get('options')
        if decorationOptions:
            if isinstance(decorationOptions.get('pillars'), list):
                nodePivot = self.structure.getHorizontalCenter()
                for pillar in decorationOptions.get('pillars'):
                    pillarPosition = mapTools.rotatePointAroundOrigin(
                        nodePivot,
                        [
                            pillar['pos'][0],
                            self.structure.y - 1,
                            pillar['pos'][1]
                        ],
                        decorationStructure.rotation
                    )
                    groundLevel = self.localHeightMapOceanFloor[
                        pillarPosition[0],
                        pillarPosition[2]
                    ]
                    pillarPosition = np.add(pillarPosition, [self.structure.x, 0, self.structure.z])
                    mapTools.fill(
                        *pillarPosition,
                        pillarPosition[0], groundLevel, pillarPosition[2],
                        pillar.get('material')
                    )

                    if pillar.get('ladder') is not None:
                        ladderRotation = (decorationStructure.rotation + pillar.get('ladder')) % 4
                        self._placeLadder(pillarPosition, ladderRotation, groundLevel)

            if decorationOptions.get('chests') is True:
                for block in decorationStructure.nbt['blocks']:

                    # Check if block has an inventory which can be filled.
                    blockMaterial = decorationStructure.getBlockMaterial(block)
                    if blockMaterial not in INVENTORY:
                        continue

                    # If less than threshold, mark inventory block as not placable.
                    if self.rng.random() < 0.5:
                        decorationStructure.markBlockAsUnplacable(block)
                        continue

                    # Get dimensions/size of the inventory block (eg. (9,3) for minecraft:chest)
                    inventoryDimensions = INVENTORYLOOKUP[blockMaterial]

                    newInventory = []

                    # Materials which can be sampled for the surroundings to put in chests.
                    natureSampleMaterials = SOILS + PLANTS + TREES

                    # For each inventory slot...
                    for inventorySlot in range(inventoryDimensions[0] * inventoryDimensions[1]):

                        # # If less than threshold, skip this inventory slot
                        if self.rng.random() < 0.5:
                            continue

                        # Get random block from ground of this node structure.
                        randomX = self.rng.integers(self.structure.getSizeX())
                        randomZ = self.rng.integers(self.structure.getSizeZ())
                        heightMapSample = self.localHeightMapOceanFloor[randomX, randomZ]
                        sampleMaterial = self.worldSlice.getBlockAt(
                            self.structure.x + randomX,
                            self.rng.integers(heightMapSample - 2, heightMapSample + 2),
                            self.structure.z + randomZ
                        )
                        if sampleMaterial not in natureSampleMaterials or sampleMaterial in AIR:
                            continue
                        newInventory.append({
                            'x': self.rng.integers(inventoryDimensions[0]),
                            'y': self.rng.integers(inventoryDimensions[1]),
                            'material': sampleMaterial,
                            'amount': self.rng.integers(1, 9)
                        })
                        # TODO add paper with science sample description
                        if self.rng.random() < 0.8:
                            continue
                        randomCodes = ''.join(self.rng.choice(list(string.hexdigits), size=10))
                        bookText = \
                            'SAMPLE REPORT §4{}§r\n'.format(randomCodes) + \
                            'date: §d{}/{}/{}:{}§r\n'.format(
                                self.rng.integers(1, 9),
                                self.rng.integers(1, 11),
                                # TODO dynasty year
                                # TODO convert local time to alien planet time (see Mars rover time logging)
                                self.rng.integers(20, 28),
                                self.rng.integers(0, 61),
                                self.rng.integers(0, 25)
                            ) + \
                            'SUBJECT: §a SOIL SAMPLE OF {}'.format(sampleMaterial)
                        bookData = mapTools.writeBook(
                            text=bookText,
                            title='$4 SAMPLE REPORT {}'.format(randomCodes),
                            author='Me'
                        )
                        newInventory.append({
                            'x': self.rng.integers(inventoryDimensions[0]),
                            'y': self.rng.integers(inventoryDimensions[1]),
                            'material': 'minecraft:written_book',
                            'amount': 1,
                            'tag': bookData
                        })

                        # TODO Add tools and scientific instruments to chests

                    mapTools.setInventoryBlockContents(
                        block,
                        blockMaterial,
                        newInventory
                    )

        decorationStructure.place()

    # Place transition structure.
    # This is a structure inserted inside of the node's structure to create a transition (eg. a doorway) to the next
    # structure. These transition structures should have the same dimensions as the Node structure.
    # Use minecraft:structure_void blocks in the transition structure to prevent replacing the entire node structure.
    def _placeTransitionStructure(self, structureFile, facing):
        Structure(
            structurePrototype=self.structure.prototype.transitionStructures[structureFile],
            rotation=facing,
            x=self.structure.x,
            y=self.structure.y,
            z=self.structure.z
        ).place()

    def _chooseNextStructure(self, placementScores):
        if placementScores is None or len(placementScores) == 0:
            return None
        valueSum = np.sum(list(placementScores.values()))
        weights = []
        for key, value in placementScores.items():
            weights.append(
                value / valueSum
            )
        weights = np.reciprocal(weights)
        weights = weights / np.sum(weights)
        return self.rng.choice(list(placementScores), p=weights)

    def place(self, isStartingNode=False):

        self.structure.place()
        self._updateMapOfStructures(self.structure)

        self._doPostProcessing()

        selfRotation = self.structure.rotation
        for connection in self.connectors:

            connectionRotation = (connection.get('facing') + selfRotation) % 4

            isPreviousDirection = False
            placementScores = dict()
            nextNodeCandidates = dict()

            if isStartingNode is False and (connection.get('facing') + selfRotation + 2) % 4 == selfRotation:
                isPreviousDirection = True
            elif isinstance(connection.get('nextStructure'), list):

                nextStructureNameList = copy.copy(connection.get('nextStructure'))
                self.rng.shuffle(nextStructureNameList)

                for nextStructureName in nextStructureNameList:
                    if nextStructureName not in globals.structurePrototypes:
                        continue

                    nextStructure = globals.structurePrototypes[nextStructureName]

                    # Determine height of next node.
                    nextHeight = self.structure.y
                    if connection.get('height'):
                        nextHeight = self.structure.y + connection.get('height')

                    # Construct node and evaluate placement score
                    nextNodeCandidates[nextStructureName] = Node(
                        nodeStructurePrototype=nextStructure,
                        facing=connectionRotation,
                        y=nextHeight,
                        parentStructure=self.structure,
                        buildArea=self.buildArea,
                        mapOfStructures=self.mapOfStructures,
                        rng=self.rng,
                        baseLineHeightMap=self.baseLineHeightMap,
                        oceanFloorHeightMap=self.oceanFloorHeightMap,
                        worldSlice=self.worldSlice
                    )
                    placementCost = nextNodeCandidates[nextStructureName].getPlacementCost()
                    if placementCost is not None:
                        placementScores[nextStructureName] = placementCost

            # Select next node based on which has the lowest placement cost.
            # TODO have placement looking 2 step into the future with MCTS
            nextNodeStructureName = self._chooseNextStructure(placementScores)
            nextNode = nextNodeCandidates.get(nextNodeStructureName)

            # Build transition piece
            if connection.get('transitionStructure'):
                # Only when it transitioning in the previous direction
                # OR to transition to the next node, as long this is placable.
                if isPreviousDirection or nextNode:
                    self._placeTransitionStructure(connection.get('transitionStructure'), connectionRotation)

            if nextNode:
                globals.constructionBudget -= placementScores[nextNodeStructureName]
                print('remaining construction budget: %s after placing %s (cost: %s)' % (
                    globals.constructionBudget, nextNodeStructureName, placementScores[nextNodeStructureName]
                ))
                nextNode.place()
