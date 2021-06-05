import numpy as np
from nbt import nbt
import interfaceUtils
import mapUtils
import os
import json


# With this class you can load in an NBT-encoded Minecraft Structure file
# (https://minecraft.fandom.com/wiki/Structure_Block_file_format) and place them in the world.


class Structure:
    ROTATE_NORTH = 0
    ROTATE_EAST = 1
    ROTATE_SOUTH = 2
    ROTATE_WEST = 3
    ROTATIONS = ["north", "east", "south", "west"]
    rotation = ROTATE_NORTH

    origin = [0, 0, 0]

    customProperties = {}

    debug = False

    def __init__(self,
                 structureFilePath: str,
                 x: int = 0, y: int = 0, z: int = 0,
                 rotation: int = ROTATE_NORTH,
                 rotateAroundCenter: bool = True
                 ):
        self.file = nbt.NBTFile('structures/' + structureFilePath + ".nbt", "rb")

        self.x = x
        self.y = y
        self.z = z

        if os.path.isfile('structures/' + structureFilePath + '.json'):
            with open('structures/' + structureFilePath + '.json') as JSONfile:
                self.customProperties = json.load(JSONfile)
                self._applyCustomProperties()

        self.setRotation(rotation, rotateAroundCenter)
        self.materialReplacements = dict()

    def setPosition(self, x=None, y=None, z=None):
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        if z is not None:
            self.z = z

    def setOrigin(self, x=None, y=None, z=None):
        if x is not None:
            self.origin[0] = x
        if y is not None:
            self.origin[1] = y
        if z is not None:
            self.origin[2] = z

    def setSize(self, x=None, y=None, z=None):
        if x is not None:
            self.file["size"][0].value = x
        if y is not None:
            self.file["size"][1].value = y
        if z is not None:
            self.file["size"][2].value = z

    # TODO apply rotation only on placement, not before.
    def setRotation(self, rotation, rotateAroundCenter=False):
        if rotation is not None and 0 <= rotation <= 3:
            self.rotation = rotation

        # Change position of blocks inside structure to match rotation.
        if rotation != self.ROTATE_NORTH:
            for block in self.file["blocks"]:
                currentPosition = [
                    block["pos"][0].value,
                    block["pos"][1].value,
                    block["pos"][2].value
                ]
                pivot = self.origin if not rotateAroundCenter else self.getHorizontalCenter()
                newPosition = mapUtils.rotatePointAroundOrigin(pivot, currentPosition, rotation)
                block["pos"][0].value = newPosition[0]
                block["pos"][1].value = newPosition[1]
                block["pos"][2].value = newPosition[2]

    def getSizeX(self):
        return self.file["size"][0].value

    def getSizeY(self):
        return self.file["size"][1].value

    def getSizeZ(self):
        return self.file["size"][2].value

    def getBox(self):
        return [
            self.x,
            self.y,
            self.z,
            self.getSizeX(),
            self.getSizeY(),
            self.getSizeZ()
        ]

    def getOriginInWorldSpace(self):
        return mapUtils.rotatePointAroundOrigin(
            [self.x, self.y, self.z],
            [
                self.x + self.origin[0],
                self.y + self.origin[1],
                self.z + self.origin[2]
            ],
            self.rotation
        )

    def getFarCornerInWorldSpace(self):
        worldSpaceOrigin = self.getOriginInWorldSpace()
        return mapUtils.rotatePointAroundOrigin(
            worldSpaceOrigin,
            [
                worldSpaceOrigin[0] + (self.getSizeX() - self.origin[0]),
                worldSpaceOrigin[1] + (self.getSizeY() - self.origin[1]),
                worldSpaceOrigin[2] + (self.getSizeZ() - self.origin[2])
            ],
            self.rotation
        )

    def getHorizontalCenter(self):
        return [
            int(np.round(self.getSizeX() / 2)),
            self.origin[1],
            int(np.round(self.getSizeZ() / 2))
        ]

    def getShortestDimension(self):
        if self.rotation % 2 == 0:
            return np.argmin([np.abs(self.getSizeX()), np.abs(self.getSizeY()), np.abs(self.getSizeZ())])
        return np.argmin([np.abs(self.getSizeZ()), np.abs(self.getSizeY()), np.abs(self.getSizeX())])

    def getLongestDimension(self):
        if self.rotation % 2 == 0:
            return np.argmax([np.abs(self.getSizeX()), np.abs(self.getSizeY()), np.abs(self.getSizeZ())])
        return np.argmax([np.abs(self.getSizeZ()), np.abs(self.getSizeY()), np.abs(self.getSizeX())])

    def getShortestHorizontalDimension(self):
        if self.rotation % 2 == 0:
            return np.argmin([np.abs(self.getSizeX()), np.abs(self.getSizeZ())]) * 2
        return np.argmin([np.abs(self.getSizeZ()), np.abs(self.getSizeX())]) * 2

    def getLongestHorizontalDimension(self):
        if self.rotation % 2 == 0:
            return np.argmax([np.abs(self.getSizeX()), np.abs(self.getSizeZ())]) * 2
        return np.argmax([np.abs(self.getSizeZ()), np.abs(self.getSizeX())]) * 2

    def getShortestSize(self):
        if self.rotation % 2 == 0:
            return [self.getSizeX(), self.getSizeY(), self.getSizeZ()][self.getShortestDimension()]
        return [self.getSizeZ(), self.getSizeY(), self.getSizeX()][self.getShortestDimension()]

    def getLongestSize(self):
        if self.rotation % 2 == 0:
            return [self.getSizeX(), self.getSizeY(), self.getSizeZ()][self.getLongestDimension()]
        return [self.getSizeZ(), self.getSizeY(), self.getSizeX()][self.getLongestDimension()]

    def getShortestHorizontalSize(self):
        if self.rotation % 2 == 0:
            return [self.getSizeX(), 0, self.getSizeZ()][self.getShortestHorizontalDimension()]
        return [self.getSizeZ(), 0, self.getSizeX()][self.getShortestHorizontalDimension()]

    def getLongestHorizontalSize(self):
        if self.rotation % 2 == 0:
            return [self.getSizeX(), 0, self.getSizeZ()][self.getLongestHorizontalDimension()]
        return [self.getSizeZ(), 0, self.getSizeX()][self.getLongestHorizontalDimension()]

    # Add dict of materials from the structure file that need replaced with something else.
    # eg. "minecraft:iron_block", "minecraft:gold_block" will put gold blocks where the structure file has iron blocks
    # when placing the structure in the world.
    def replaceMaterial(self, existingMaterial, newMaterial):
        self.materialReplacements[existingMaterial] = newMaterial

    # Apply custom properties from the custom properties file which are relevant for the structure as an
    # independent structure.
    def _applyCustomProperties(self):
        if 'effectiveSpace' in self.customProperties:
            customEffectiveSpace = self.customProperties['effectiveSpace']
            self.setOrigin(*customEffectiveSpace[:3])
            self.setSize(*customEffectiveSpace[3:])

    def _getBlockMaterial(self, block):
        blockMaterial = self.file["palette"][block["state"].value]['Name'].value
        replacementMaterial = self.materialReplacements.get(blockMaterial)
        if replacementMaterial is None:
            return blockMaterial
        return replacementMaterial

    # Get block properties (also known as block states: https://minecraft.fandom.com/wiki/Block_states) of a block.
    # This may contain information on the orientation of a block or open or closed stated of a door.
    def _getBlockProperties(self, block):
        properties = dict()
        if "Properties" in self.file["palette"][block["state"].value].keys():
            for key in self.file["palette"][block["state"].value]["Properties"].keys():
                properties[key] = self.file["palette"][block["state"].value]["Properties"][key].value

                # Apply rotation to block property if needed.
                if key == "facing" and self.rotation != self.ROTATE_NORTH:
                    properties[key] = self.ROTATIONS[
                        (self.ROTATIONS.index(properties[key]) + self.rotation) % len(self.ROTATIONS)
                        ]
                if key == "axis" and (self.rotation == self.ROTATE_EAST or self.rotation == self.ROTATE_WEST):
                    if properties[key] == "x":
                        properties[key] = "z"
                    elif properties[key] == "z":
                        properties[key] = "x"

        return properties

    @staticmethod
    def getStructuresInDir(structureDir=""):
        structureList = []
        for file in os.listdir("./structures/" + structureDir):
            if file.endswith(".nbt"):
                structureList.append(structureDir + "/" + file.replace(".nbt", ""))
        return structureList

    def getMaterialList(self):
        materials = []
        for block in self.file["blocks"]:
            blockMaterial = self._getBlockMaterial(block)
            if blockMaterial not in materials:
                materials.append(blockMaterial)
        return materials

    def place(self, includeAir=False):
        for block in self.file["blocks"]:
            blockMaterial = self._getBlockMaterial(block)

            if blockMaterial == 'minecraft:structure_void':
                continue

            # Skip empty parts of the structure unless includeAir is True.
            if includeAir is False and blockMaterial == "minecraft:air":
                continue

            blockPosition = [
                block["pos"][0].value + self.x,
                block["pos"][1].value + self.y,
                block["pos"][2].value + self.z
            ]
            blockProperties = self._getBlockProperties(block)
            mapUtils.setBlock(blockPosition[0], blockPosition[1], blockPosition[2], blockMaterial, blockProperties)

        interfaceUtils.sendBlocks()

        if self.debug:
            mapUtils.fill(
                *self.getOriginInWorldSpace(),
                *self.getOriginInWorldSpace(),
                "minecraft:orange_wool"
            )
            mapUtils.fill(
                *self.getFarCornerInWorldSpace(),
                *self.getFarCornerInWorldSpace(),
                "minecraft:purple_wool"
            )
