import numpy as np
import re

import mapUtils
from Structure import Structure


class Node:

    connectors = []

    def __init__(self,
                 x: int = 0, y: int = 0, z: int = 0,
                 heightMap=np.array([]),
                 rotation: int = Structure.ROTATE_NORTH,
                 previousRotation = None,
                 nodeStructureType: str = ''
                 ):

        self.rng = np.random.default_rng()

        self.heightMap = heightMap

        self.nodeStructureType = nodeStructureType
        nodeStructureFile = re.sub(r"^.+/", "", nodeStructureType)
        self.structure = Structure(
            structureFilePath=nodeStructureType + "/" + nodeStructureFile,
            x=x, y=y, z=z,
            rotation=rotation
        )

        if 'connectors' in self.structure.customProperties:
            if isinstance(self.structure.customProperties['connectors'], list):
                self.connectors = [
                    item for item in self.structure.customProperties['connectors']
                    if item.get('facing') != previousRotation
                ]

        # Pick a next node for each connector
        for connection in self.connectors:
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
        nodeOrigin = self.structure.getOriginInWorldSpace()
        for pillar in pillars:
            pillarPosition = mapUtils.rotatePointAroundOrigin(
                nodeOrigin,
                [
                    self.structure.x + pillar['pos'][0],
                    self.structure.y - 1,
                    self.structure.z + pillar['pos'][1]
                ],
                self.structure.rotation
            )
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
            if connection.get('nextStructure') is None:
                continue

            facing = connection.get('facing')

            # Build transition piece
            if connection.get('transitionStructure'):
                Structure(
                    structureFilePath=self.nodeStructureType + '/' + connection.get('transitionStructure'),
                    rotation=facing,
                    x=self.structure.x,
                    y=self.structure.y,
                    z=self.structure.z
                ).place(includeAir=True)

            # Init and place next node
            # TODO last argument should be next structure, not the current one.
            nextPosition = mapUtils.getNextPosition(facing, self.structure.getBox(), self.structure.getBox())
            nextNode = Node(
                nodeStructureType=connection.get('nextStructure'),
                rotation=facing,
                previousRotation=self.structure.rotation,
                x=nextPosition[0],
                y=self.structure.y,
                z=nextPosition[2],
                heightMap=self.heightMap
            )
            nextNode.place()
