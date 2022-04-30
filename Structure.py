import copy
import numpy as np
from StructurePrototype import StructurePrototype
import interface
import mapTools

# With this class you can load in an NBT-encoded Minecraft Structure file
# (https://minecraft.fandom.com/wiki/Structure_Block_file_format) and place them in the world.


class Structure:

    ROTATE_NORTH = 0
    ROTATE_EAST = 1
    ROTATE_SOUTH = 2
    ROTATE_WEST = 3
    ROTATIONS = ["north", "east", "south", "west"]

    debug = False

    def __init__(self,
                 structurePrototype: StructurePrototype,
                 x: int = 0, y: int = 0, z: int = 0,
                 rotation: int = ROTATE_NORTH,
                 rotateAroundCenter: bool = True
                 ):
        self.prototype = structurePrototype

        self.nbt = structurePrototype.nbt

        self.x = x
        self.y = y
        self.z = z
        self.origin = [0, 0, 0]
        self.rotation = rotation

        self.rotateAroundCenter = rotateAroundCenter

        self.customProperties = copy.deepcopy(structurePrototype.customProperties)
        self._applyCustomProperties()

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
            self.nbt["size"][0].value = x
        if y is not None:
            self.nbt["size"][1].value = y
        if z is not None:
            self.nbt["size"][2].value = z

    def getSizeX(self):
        return self.nbt["size"][0].value

    def getSizeY(self):
        return self.nbt["size"][1].value

    def getSizeZ(self):
        return self.nbt["size"][2].value

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
        return np.add(
            self.origin,
            [self.x, self.y, self.z]
        )

    def getFarCornerInWorldSpace(self):
        return np.add(
            [
                self.getSizeX() - self.origin[0],
                self.getSizeY() - self.origin[1],
                self.getSizeZ() - self.origin[2]
            ],
            self.getOriginInWorldSpace()
        )

    def getHorizontalCenter(self):
        return [
            int(np.round(self.getSizeX() / 2)),
            self.origin[1],
            int(np.round(self.getSizeZ() / 2))
        ]

    def getShortestDimension(self):
        return np.argmin([np.abs(self.getSizeX()), np.abs(self.getSizeY()), np.abs(self.getSizeZ())])

    def getLongestDimension(self):
        return np.argmax([np.abs(self.getSizeX()), np.abs(self.getSizeY()), np.abs(self.getSizeZ())])

    def getShortestHorizontalDimension(self):
        return np.argmin([np.abs(self.getSizeX()), np.abs(self.getSizeZ())]) * 2

    def getLongestHorizontalDimension(self):
        return np.argmax([np.abs(self.getSizeX()), np.abs(self.getSizeZ())]) * 2

    def getShortestSize(self):
        return [self.getSizeX(), self.getSizeY(), self.getSizeZ()][self.getShortestDimension()]

    def getLongestSize(self):
        return [self.getSizeX(), self.getSizeY(), self.getSizeZ()][self.getLongestDimension()]

    def getShortestHorizontalSize(self):
        return [self.getSizeX(), 0, self.getSizeZ()][self.getShortestHorizontalDimension()]

    def getLongestHorizontalSize(self):
        return [self.getSizeX(), 0, self.getSizeZ()][self.getLongestHorizontalDimension()]

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
        if 'offset' in self.customProperties:
            customOffset = self.customProperties['offset']
            self.setPosition(
                self.x + customOffset[0],
                self.y + customOffset[1],
                self.z + customOffset[2]
            )

    def _getBlockMaterial(self, block):
        blockMaterial = self.nbt["palette"][block["state"].value]['Name'].value
        replacementMaterial = self.materialReplacements.get(blockMaterial)
        if replacementMaterial is None:
            return blockMaterial
        return replacementMaterial

    # Get block properties (also known as block states: https://minecraft.fandom.com/wiki/Block_states) of a block.
    # This may contain information on the orientation of a block or open or closed stated of a door.
    def _getBlockProperties(self, block):
        properties = dict()
        if "Properties" in self.nbt["palette"][block["state"].value].keys():
            for key in self.nbt["palette"][block["state"].value]["Properties"].keys():
                properties[key] = self.nbt["palette"][block["state"].value]["Properties"][key].value

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

    def _applyRotation(self, block):
        currentPosition = [
            block["pos"][0].value,
            block["pos"][1].value,
            block["pos"][2].value
        ]
        if self.rotation == self.ROTATE_NORTH:
            return currentPosition

        pivot = self.origin if not self.rotateAroundCenter else self.getHorizontalCenter()
        return mapTools.rotatePointAroundOrigin(pivot, currentPosition, self.rotation)

    def getMaterialList(self):
        materials = []
        for block in self.nbt["blocks"]:
            blockMaterial = self._getBlockMaterial(block)
            if blockMaterial not in materials:
                materials.append(blockMaterial)
        return materials

    def place(self, includeAir=False):
        for block in self.nbt["blocks"]:
            blockMaterial = self._getBlockMaterial(block)

            if blockMaterial == 'minecraft:structure_void':
                continue

            # Skip empty parts of the structure unless includeAir is True.
            if includeAir is False and blockMaterial == "minecraft:air":
                continue

            blockPosition = np.add(self._applyRotation(block), [self.x, self.y, self.z])
            blockProperties = self._getBlockProperties(block)
            mapTools.setBlock(blockPosition[0], blockPosition[1], blockPosition[2], blockMaterial, blockProperties)

        interface.sendBlocks()

        if self.debug:
            mapTools.fill(
                *self.getOriginInWorldSpace(),
                *self.getOriginInWorldSpace(),
                "minecraft:orange_wool"
            )
            mapTools.fill(
                *self.getFarCornerInWorldSpace(),
                *self.getFarCornerInWorldSpace(),
                "minecraft:purple_wool"
            )
