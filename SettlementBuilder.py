import mapUtils
from Node import Node


class SettlementBuilder:

    def __init__(self):

        buildArea = mapUtils.getBuildArea()
        startingPos = (5, 5)

        heightMap = mapUtils.calcGoodHeightmap(buildArea)[startingPos[0]:, startingPos[1]:]

        startingNode = Node(
            x=buildArea[0] + startingPos[0],
            y=73,
            z=buildArea[1] + startingPos[1],
            heightMap=heightMap,
            nodeStructureType='lab_a/hub'
        )
        startingNode.place()
