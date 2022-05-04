import numpy as np
import mapTools
from Node import Node
import globals
import StructurePrototype


class SettlementBuilder:

    def __init__(self):

        # DEBUG
        # central RNG generator
        self.rng = np.random.default_rng()

        # /setbuildarea ~ ~ ~ ~32 ~12 ~32
        self.buildArea = mapTools.getBuildArea()

        # DEBUG
        # mapTools.fill(
        #     buildArea[0],
        #     69,
        #     buildArea[1],
        #     buildArea[0] + buildArea[2],
        #     69 + 10,
        #     buildArea[1] + buildArea[3],
        #     "minecraft:air"
        # )
        #
        # # DEBUG
        # mapTools.placePerimeter(
        #     buildArea[0],
        #     68,
        #     buildArea[1],
        #     buildArea[0] + buildArea[2],
        #     68,
        #     buildArea[1] + buildArea[3],
        #     'minecraft:orange_wool'
        # )

        # Height map of the build area.
        self.baseLineHeightMap, self.oceanFloorHeightMap = mapTools.calcHeightMap(self.buildArea)

        # Map of structures built in the build area.
        mapOfStructures = np.full(shape=self.baseLineHeightMap.shape, fill_value=0)

        startingStructure: StructurePrototype = globals.structurePrototypes['ladder']

        maxPlacementAttempts = 40
        placementTryCount = 0
        while placementTryCount < maxPlacementAttempts:

            startingPos = self.getStartPosition(startingStructure)

            startingNode = Node(
                x=startingPos[0],
                y=startingPos[1],
                z=startingPos[2],
                facing=self.rng.integers(4),
                buildArea=self.buildArea,
                mapOfStructures=mapOfStructures,
                nodeStructurePrototype=startingStructure,
                rng=self.rng
            )
            print(
                'Trying placing starting structure %s at %s (%s)' % (
                    startingStructure.structureName, startingPos, placementTryCount + 1
                )
            )
            if startingNode.isPlacable():
                startingNode.place(isStartingNode=True)
                break
            else:
                placementTryCount = placementTryCount + 1

    def getStartPosition(self, startingStructure):
        # Pick starting position somewhere in the middle of the build area
        structureSize = startingStructure.getLongestHorizontalSize()
        pos = (
            self.rng.integers(low=structureSize, high=self.buildArea[2] - structureSize),
            0,
            self.rng.integers(low=structureSize, high=self.buildArea[3] - structureSize)
        )
        pos = (
            pos[0] + self.buildArea[0] + int(startingStructure.getSizeX() / 2),
            self.baseLineHeightMap[pos[0], pos[2]] + startingStructure.groundClearance,
            pos[2] + self.buildArea[1] + int(startingStructure.getSizeZ() / 2)
        )
        return pos

