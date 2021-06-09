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
                 facing: int = None,
                 nodeStructureType: str = ''
                 ):

        # Create random generator for this Node instance.
        self.rng = np.random.default_rng()

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
            globalFarCorner=self.structure.getFarCornerInWorldSpace()
        )
        self.heightMap = heightMap
        self.buildArea = buildArea

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
        return True

    # Run function for each post-processing step.
    def _doPostProcessing(self):
        if isinstance(self.structure.customProperties.get('postProcessing'), list):
            for operations in self.structure.customProperties.get('postProcessing'):
                if 'placePillars' in operations:
                    self._placePillars(operations['placePillars'])

    # Place pillars post-processing fucntion.
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
            mapUtils.fill(
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

    def place(self):
        if not self.isPlacable():
            return

        self.structure.place()

        self._doPostProcessing()

        for connection in self.connectors:
            facing = (connection.get('facing') + self.structure.rotation) % 4
            nextNode = None

            if connection.get('nextStructure'):
                # Init and place next node
                nextNode = Node(
                    nodeStructureType=connection.get('nextStructure'),
                    facing=facing,
                    parentStructure=self.structure,
                    buildArea=self.buildArea,
                    heightMap=self.heightMap
                )

            # Build transition piece
            if connection.get('transitionStructure'):
                # Only when it transitioning in the previous direction
                # OR to transition to the next node, as long this is placable.
                if connection.get('isPreviousDirection') or (connection.get('nextStructure') and nextNode.isPlacable()):
                    Structure(
                        structureFilePath=self.nodeStructureType + '/' + connection.get('transitionStructure'),
                        rotation=facing,
                        x=self.structure.x,
                        y=self.structure.y,
                        z=self.structure.z
                    ).place(includeAir=True)

            if nextNode:
                nextNode.place()
