import numpy as np
import re

import mapUtils
from Structure import Structure


class Node:

    connectors = []

    def __init__(self,
                 x: int = 0, y: int = 0, z: int = 0,
                 parentStructure: Structure = None,
                 buildArea=(0, 0, 0, 0),
                 heightMap=np.array([]),
                 mapOfStructures=np.array([]),
                 facing: int = None,
                 nodeStructureType: str = '',
                 rng=np.random.default_rng()
                 ):

        self.rng = rng
        self.buildArea = buildArea
        self.heightMap = heightMap
        self.mapOfStructures = mapOfStructures

        # Construct file path
        self.nodeStructureType = nodeStructureType
        nodeStructureFile = re.sub(r"^.+/", "", nodeStructureType)

        # Create structure instance.
        self.structure = Structure(
            structureFilePath=nodeStructureType + "/" + nodeStructureFile,
            x=x, y=y, z=z,
            rotation=Structure.ROTATE_NORTH if facing is None else facing
        )

        # Translate structure position depending on facing direction.
        if facing is not None and parentStructure is not None:
            self.structure.setPosition(
                *mapUtils.getNextPosition(facing, parentStructure.getBox(), self.structure.getBox())
            )

        # Create cropped heightmap for the ground underneath the structure.
        self.localHeightMap = mapUtils.getCroppedGrid(
            grid=heightMap,
            globalOrigin=buildArea[:2],
            globalCropOrigin=self.structure.getOriginInWorldSpace(),
            globalCropFarCorner=self.structure.getFarCornerInWorldSpace()
        )

        # Bind connectors list from structure's custom properties.
        if 'connectors' in self.structure.customProperties:
            if isinstance(self.structure.customProperties['connectors'], list):
                self.connectors = self.structure.customProperties['connectors']

        # Pick a next node for each connector
        for connection in self.connectors:
            # If current node has a defined facing direciton and it's the opposite of the connection's direction:
            if facing is not None and (connection.get('facing') + facing + 2) % 4 == facing:
                connection['isPreviousDirection'] = True
                connection['nextStructure'] = None
            else:
                # TODO pick nextStructure based on weighted value based on some evaluation function.
                connection['nextStructure'] = self.rng.choice(connection.get('nextStructure'))

    # Evaluate if the current structure is placable.
    def isPlacable(self):
        if self.localHeightMap.shape != (self.structure.getSizeX(), self.structure.getSizeZ()):
            return False

        structureMapCropped = mapUtils.getCroppedGrid(
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
        localOrigin, localFarCorner = mapUtils.getCrop(
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
            pillarPosition = mapUtils.rotatePointAroundOrigin(
                nodePivot,
                [
                    pillar['pos'][0],
                    self.structure.y - 1,
                    pillar['pos'][1]
                ],
                self.structure.rotation
            )
            groundLevel = self.localHeightMap[
                pillarPosition[0],
                pillarPosition[2]
            ]
            pillarPosition = np.add(pillarPosition, [self.structure.x, 0, self.structure.z])
            mapUtils.keepFill(
                *pillarPosition,
                pillarPosition[0], groundLevel, pillarPosition[2],
                pillar.get('material')
            )
            # If pillar has a facing direction for a ladder defined, put a ladder on this face of the pillar.
            if pillar.get('ladder') is not None:
                ladderRotation = (self.structure.rotation + pillar.get('ladder')) % 4
                ladderPosition = mapUtils.rotatePointAroundOrigin(
                    pillarPosition,
                    np.add(pillarPosition, [0, 0, -1]),
                    ladderRotation
                )
                for ladderY in range(groundLevel, self.structure.y):
                    mapUtils.setBlock(
                        ladderPosition[0], ladderY, ladderPosition[2],
                        'ladder',
                        {
                            'facing': Structure.ROTATIONS[ladderRotation]
                        }
                    )

    # Place decoration structures post-processing function.
    def _placeDecorations(self, decorations):
        for decorationTypes in decorations:
            # For each sub-list of decorations, pick only one.
            decoration = self.rng.choice(decorationTypes)
            if decoration is None:
                continue

            # Pick random orientation for decoration or one of the pre-defined directions.
            facing = self.rng.integers(4)
            if isinstance(decoration.get('facing'), list):
                facing = self.rng.choice(decoration.get('facing'))

            decorationOrigin = [0, 0, 0]
            if isinstance(decoration.get('origin'), list) and len(decoration.get('origin')) == 3:
                decorationOrigin = decoration.get('origin')

            Structure(
                structureFilePath=self.nodeStructureType + '/' + decoration.get('decorationStructure'),
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
            structureFilePath=self.nodeStructureType + '/' + structureFile,
            rotation=facing,
            x=self.structure.x,
            y=self.structure.y,
            z=self.structure.z
        ).place(includeAir=True)

    def place(self):
        if not self.isPlacable():
            return

        self.structure.place()
        self._updateMapOfStructures(self.structure)

        self._doPostProcessing()

        for connection in self.connectors:
            facing = (connection.get('facing') + self.structure.rotation) % 4

            # Determine height of next node.
            nextHeight = self.structure.y
            if connection.get('height'):
                nextHeight = self.structure.y + connection.get('height')

            nextNode = None

            if connection.get('nextStructure'):
                # Init and place next node
                nextNode = Node(
                    nodeStructureType=connection.get('nextStructure'),
                    facing=facing,
                    y=nextHeight,
                    parentStructure=self.structure,
                    buildArea=self.buildArea,
                    heightMap=self.heightMap,
                    mapOfStructures=self.mapOfStructures,
                    rng=self.rng
                )

            # Build transition piece
            if connection.get('transitionStructure'):
                # Only when it transitioning in the previous direction
                # OR to transition to the next node, as long this is placable.
                if connection.get('isPreviousDirection') or (connection.get('nextStructure') and nextNode.isPlacable()):
                    self._placeTransitionStructure(connection.get('transitionStructure'), facing)

            if nextNode:
                nextNode.place()
