from StructurePrototype import StructurePrototype
import glob
import re

global structurePrototypes


def initialize():
    global structurePrototypes
    structurePrototypes = dict()
    loadStructures()


def loadStructures():
    for mainStructureFolder in glob.glob('structures/*/'):
        structureFileName = re.sub(r'^.+/(.+)/$', r'\1', mainStructureFolder)

        structureFilePath = mainStructureFolder + '/' + structureFileName

        structurePrototypes[structureFileName] = StructurePrototype(
            structureFilePath=structureFilePath
        )


