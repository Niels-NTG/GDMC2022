import numpy as np
import re

import mapUtils
from Structure import Structure


class Node:

    connectors = []

    def __init__(self,
                 x: int = 0, y: int = 0, z: int = 0,
                 parentStructure: Structure = None,
                 heightMap=np.array([]),
                 facing: int = None,
                 nodeStructureType: str = ''
                 ):

        self.rng = np.random.default_rng()

        self.heightMap = heightMap

        self.nodeStructureType = nodeStructureType
        nodeStructureFile = re.sub(r"^.+/", "", nodeStructureType)
        self.structure = Structure(
            structureFilePath=nodeStructureType + "/" + nodeStructureFile,
            x=x, y=y, z=z,
            rotation=Structure.ROTATE_NORTH if facing is None else facing
        )
        if facing is not None and parentStructure is not None:
            self.structure.setPosition(
                *mapUtils.getNextPosition(facing, parentStructure.getBox(), self.structure.getBox())
            )

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
                # TODO pick nextStructure based on random weighed value
                connection['nextStructure'] = self.rng.choice(connection.get('nextStructure'))

    def _doPostProcessing(self):
        if isinstance(self.structure.customProperties.get('postProcessing'), list):
            for operations in self.structure.customProperties.get('postProcessing'):
                if 'placePillars' in operations:
                    self._placePillars(operations['placePillars'])

    def _placePillars(self, pillars):
        if not isinstance(pillars, list):
            pass
        nodePivot = self.structure.getHorizontalCenter()
        for pillar in pillars:
            pillarPosition = np.add(mapUtils.rotatePointAroundOrigin(
                nodePivot,
                [
                    pillar['pos'][0],
                    self.structure.y - 1,
                    pillar['pos'][1]
                ],
                self.structure.rotation
            ), [self.structure.x, 0, self.structure.z])
            groundLevel = self.heightMap[
                pillarPosition[0] - self.structure.x,
                pillarPosition[2] - self.structure.z
            ]
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
        self.structure.place()

        self._doPostProcessing()

        for connection in self.connectors:
            facing = (connection.get('facing') + self.structure.rotation) % 4

            if connection.get('nextStructure') or connection.get('isPreviousDirection'):
                # Build transition piece
                if connection.get('transitionStructure'):
                    Structure(
                        structureFilePath=self.nodeStructureType + '/' + connection.get('transitionStructure'),
                        rotation=facing,
                        x=self.structure.x,
                        y=self.structure.y,
                        z=self.structure.z
                    ).place(includeAir=True)

            if connection.get('nextStructure') is None:
                continue

            # Init and place next node
            nextNode = Node(
                nodeStructureType=connection.get('nextStructure'),
                facing=facing,
                parentStructure=self.structure,
                heightMap=self.heightMap
            )
            nextNode.place()
