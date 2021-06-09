import numpy as np
import mapUtils
from Node import Node


class SettlementBuilder:

    def __init__(self):

        buildArea = mapUtils.getBuildArea()
        startingPos = (10, 10)

        heightMap = mapUtils.calcGoodHeightmap(buildArea)

        startingNode = Node(
            x=buildArea[0] + startingPos[0],
            y=73,
            z=buildArea[1] + startingPos[1],
            buildArea=buildArea,
            heightMap=heightMap,
            nodeStructureType='lab_a/hub'
        )
        startingNode.place()
