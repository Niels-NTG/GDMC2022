import numpy as np

import globals
import mapTools
from Structure import Structure
from StructurePrototype import StructurePrototype


class Node:

    def __init__(self,
                 x: int = 0, y: int = 0, z: int = 0,
                 parentStructure: Structure = None,
                 buildArea=(0, 0, 0, 0),
                 mapOfStructures=np.array([]),
                 facing: int = None,
                 nodeStructurePrototype: StructurePrototype = None,
                 rng=np.random.default_rng()
                 ):

        self.rng = rng
        self.buildArea = buildArea
        self.mapOfStructures = mapOfStructures

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
        baseLineHeightMap, oceanFloorHeightMap = mapTools.calcHeightMap(buildArea)
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

    # Evaluate if the current structure is placable.
    def isPlacable(self):
        if self.localHeightMapBaseLine.shape != (self.structure.getSizeX(), self.structure.getSizeZ()):
            return False

        # Prevent structure from burying itself underground
        if self.localHeightMapBaseLine.max() + self.structure.groundClearance > self.structure.y:
            return False

        # TODO replace with smart function that rescans the build area
        # Check if space is not already occupied by another structure
        structureMapCropped = mapTools.getCroppedGrid(
            grid=self.mapOfStructures,
            globalOrigin=self.buildArea[:2],
            globalCropOrigin=self.structure.getOriginInWorldSpace(),
            globalCropFarCorner=self.structure.getFarCornerInWorldSpace()
        )
        if np.any(structureMapCropped > 0):
            return False

        return True

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
        if isinstance(self.structure.customProperties.get('postProcessing'), list):
            for operations in self.structure.customProperties.get('postProcessing'):
                if 'pillars' in operations:
                    self._placePillars(operations['pillars'])
                if 'decorations' in operations:
                    self._placeDecorations(operations['decorations'])

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
    def _placeDecorations(self, decorations):
        # For each list of decorations, pick only one.
        decoration = self.rng.choice(decorations)
        if decoration is None:
            return

        # Pick random orientation for decoration or one of the pre-defined directions.
        facing = self.rng.integers(4)
        if isinstance(decoration.get('facing'), list):
            facing = self.rng.choice(decoration.get('facing'))

        decorationOrigin = [0, 0, 0]
        if isinstance(decoration.get('origin'), list) and len(decoration.get('origin')) == 3:
            decorationOrigin = decoration.get('origin')

        Structure(
            structurePrototype=self.structure.prototype.decorationStructures[decoration.get('decorationStructure')],
            rotation=(facing + self.structure.rotation) % 4,
            x=self.structure.x + decorationOrigin[0],
            y=self.structure.y + decorationOrigin[1],
            z=self.structure.z + decorationOrigin[2]
        ).place(includeAir=True)

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
        ).place(includeAir=True)

    def place(self, isStartingNode=False):
        if not self.isPlacable():
            return

        self.structure.place()
        self._updateMapOfStructures(self.structure)

        self._doPostProcessing()

        selfRotation = self.structure.rotation
        for connection in self.connectors:

            isPreviousDirection = False
            nextStructure = None

            if isStartingNode is False and (connection.get('facing') + selfRotation + 2) % 4 == selfRotation:
                isPreviousDirection = True
            elif isinstance(connection.get('nextStructure'), list):
                nextStructureName = self.rng.choice(connection.get('nextStructure'))
                if nextStructureName in globals.structurePrototypes:
                    nextStructure = globals.structurePrototypes[nextStructureName]
                    # TODO pick next structure for this connection using .isPlacable heuristic

            connectionRotation = (connection.get('facing') + selfRotation) % 4

            # Determine height of next node.
            nextHeight = self.structure.y
            if connection.get('height'):
                nextHeight = self.structure.y + connection.get('height')

            nextNode = None
            if nextStructure:
                # Init and place next node
                nextNode = Node(
                    nodeStructurePrototype=nextStructure,
                    facing=connectionRotation,
                    y=nextHeight,
                    parentStructure=self.structure,
                    buildArea=self.buildArea,
                    mapOfStructures=self.mapOfStructures,
                    rng=self.rng
                )

            # Build transition piece
            if connection.get('transitionStructure'):
                # Only when it transitioning in the previous direction
                # OR to transition to the next node, as long this is placable.
                if isPreviousDirection or (nextNode and nextNode.isPlacable()):
                    self._placeTransitionStructure(connection.get('transitionStructure'), connectionRotation)

            if nextNode:
                nextNode.place()
