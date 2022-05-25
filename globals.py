from StructurePrototype import StructurePrototype
import glob
import re

global structurePrototypes
global constructionBudget


def initialize():
    global structurePrototypes
    structurePrototypes = dict()
    loadStructures()
    global constructionBudget


def loadStructures():
    for mainStructureFolder in glob.glob('structures11/*/'):
        structureFileName = re.sub(r'^.+/(.+)/$', r'\1', mainStructureFolder)

        structureFilePath = mainStructureFolder + '/' + structureFileName

        structurePrototypes[structureFileName] = StructurePrototype(
            structureFilePath=structureFilePath,
            structureName=structureFileName
        )


AXES = ('x', 'y', 'z')
DIRECTIONS = ('top', 'bottom', 'north', 'east', 'south', 'west')
INVERTDIRECTION = {'top': 'bottom', 'bottom': 'top',
                   'north': 'south', 'east': 'west',
                   'south': 'north', 'west': 'east'}
DIRECTION2VECTOR = {'top': (0, 1, 0), 'bottom': (0, -1, 0),
                    'north': (0, 0, -1), 'east': (1, 0, 0),
                    'south': (0, 1), 'west': (-1, 0)}
AXIS2VECTOR = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}
