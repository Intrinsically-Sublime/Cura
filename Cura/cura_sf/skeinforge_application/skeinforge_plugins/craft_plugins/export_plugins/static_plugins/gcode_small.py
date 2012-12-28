"""
This page is in the table of contents.
Gcode_small is an export plugin to remove the comments and the redundant z and feed rate parameters from a gcode file.

An export plugin is a script in the export_plugins folder which has the getOutput function, the globalIsReplaceable variable and if it's output is not replaceable, the writeOutput function.  It is meant to be run from the export tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getOutput function of this script takes a gcode text and returns that text without comments and redundant z and feed rate parameters.  The writeOutput function of this script takes a gcode text and writes that text without comments and redundant z and feed rate parameters to a file.

Many of the functions in this script are copied from gcodec in skeinforge_utilities.  They are copied rather than imported so developers making new plugins do not have to learn about gcodec, the code here is all they need to learn.

"""

from __future__ import absolute_import
import cStringIO
import os

from Cura.util import profile

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


# This is true if the output is text and false if it is binary."
globalIsReplaceable = True


def getIndexOfStartingWithSecond(letter, splitLine):
	"Get index of the first occurence of the given letter in the split line, starting with the second word.  Return - 1 if letter is not found"
	for wordIndex in xrange( 1, len(splitLine) ):
		word = splitLine[ wordIndex ]
		firstLetter = word[0]
		if firstLetter == letter:
			return wordIndex
	return - 1

def getOutput(gcodeText):
	'Get the exported version of a gcode file.'
	return GcodeSmallSkein().getCraftedGcode(gcodeText)

def getSplitLineBeforeBracketSemicolon(line):
	"Get the split line before a bracket or semicolon."
	bracketSemicolonIndex = min( line.find(';'), line.find('(') )
	if bracketSemicolonIndex < 0:
		return line.split()
	return line[ : bracketSemicolonIndex ].split()

def getStringFromCharacterSplitLine(character, splitLine):
	"Get the string after the first occurence of the character in the split line."
	indexOfCharacter = getIndexOfStartingWithSecond(character, splitLine)
	if indexOfCharacter < 0:
		return None
	return splitLine[indexOfCharacter][1 :]

def getSummarizedFileName(fileName):
	"Get the fileName basename if the file is in the current working directory, otherwise return the original full name."
	if os.getcwd() == os.path.dirname(fileName):
		return os.path.basename(fileName)
	return fileName

def getTextLines(text):
	"Get the all the lines of text of a text."
	return text.replace('\r', '\n').split('\n')


class GcodeSmallSkein(object):
	"A class to remove redundant z and feed rate parameters from a skein of extrusions."
	def __init__(self):
		self.lastFeedRateString = None
		self.lastZString = None
		self.output = cStringIO.StringIO()
		self.layerNr = 0
		self.parsingAlteration = False
		self.bridgeLayer = False
		self.fanLayer = 0
		self.fanEnabled = False
		self.bridge = 0
		self.fill = 0
		self.perim = 0
		self.support = 0
		self.bridgeFan = '\n'
		self.perimFan = '\n'
		self.fillFan = '\n'
		self.supportFan = '\n'

	def getCraftedGcode( self, gcodeText ):
		"Parse gcode text and store the gcode."
		lines = getTextLines(gcodeText)
		for line in lines:
			self.parseLine(line)
		return self.output.getvalue()

	def parseLine(self, line):
		"Parse a gcode line."
		if len(line) < 1:
			return
		if line[0] == '(':
			self.parseComment(line)
			return
		splitLine = getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if len(firstWord) < 1:
			return
		if firstWord[0] == '(':
			return
		if firstWord == 'M108' or firstWord == 'M113':
			return
		if firstWord != 'G1':
			self.output.write(line + '\n')
			return
		eString = getStringFromCharacterSplitLine('E', splitLine )
		xString = getStringFromCharacterSplitLine('X', splitLine )
		yString = getStringFromCharacterSplitLine('Y', splitLine )
		zString = getStringFromCharacterSplitLine('Z', splitLine )
		feedRateString = getStringFromCharacterSplitLine('F', splitLine )
		self.output.write('G1')
		if xString != None:
			self.output.write(' X' + xString )
		if yString != None:
			self.output.write(' Y' + yString )
		if zString != None and zString != self.lastZString:
			self.output.write(' Z' + zString )
		if feedRateString != None and feedRateString != self.lastFeedRateString:
			self.output.write(' F' + feedRateString )
		if eString != None:
			self.output.write(' E' + eString )
		self.lastFeedRateString = feedRateString
		self.lastZString = zString
		self.output.write('\n')
	
	def parseComment(self, line):
		#Check to see at which layer the fans should be turned on
		self.fanLayer = profile.getProfileSettingFloat('fan_layer')
		#Get fan speeds from profile and determine if they are on and at what speed
		#Create string so be inserted for fans
		self.bridge = (profile.getProfileSettingFloat('fan_bridge') * 255 / 100)
		self.fanEnabled = profile.getProfileSetting("fan_enabled")
		if (self.bridge > 0 and self.fanEnabled == 'True'):
			self.bridgeFan = ('\n;FAN:BRIDGE\nM106 S%d\n') % (self.bridge)
		self.perim = (profile.getProfileSettingFloat('fan_perimeter') * 255 / 100)
		if (self.perim > 0 and self.fanEnabled == 'True'):
			self.perimFan = ('\n;FAN:PERIM\nM106 S%d\n') % (self.perim)
		self.fill = (profile.getProfileSettingFloat('fan_infill') * 255 / 100)
		if (self.fill > 0 and self.fanEnabled == 'True'):
			self.fillFan = ('\n;FAN:FILL\nM106 S%d\n') % (self.fill)
		self.support = (profile.getProfileSettingFloat('fan_support') * 255 / 100)
		if (self.support > 0 and self.fanEnabled == 'True'):
			self.supportFan = ('\n;FAN:SUPPORT\nM106 S%d\n') % (self.support)		
		
		if line.startswith('(<skirt>'):
			self.output.write(';TYPE:SKIRT\n');
		elif line.startswith('(<layer>'):
			self.output.write(';LAYER:%d \n' % (self.layerNr)); #Space between %d and \n is required for post processing
			self.layerNr += 1
			self.bridgeLayer = False;
		elif line.startswith('(<bridgeRotation>'):
			self.output.write(';BRIDGE-LAYER\n');
			self.bridgeLayer = True;
		elif line.startswith('(<edge>'):
			if (self.bridgeLayer):
				self.output.write(';TYPE:OUTER:BRIDGE%s' % (self.bridgeFan));
			elif (self.layerNr > self.fanLayer):
				self.output.write(';TYPE:WALL:OUTER%s' % (self.perimFan));
			else:
				self.output.write(';TYPE:WALL:OUTER\n');
		elif line.startswith('(<loop>'):
			if (self.bridgeLayer):
				self.output.write(';TYPE:INNER:BRIDGE%s' % (self.bridgeFan));
			elif (self.layerNr > self.fanLayer):
				self.output.write(';TYPE:WALL:INNER%s' % (self.perimFan));
			else:
				self.output.write(';TYPE:WALL:INNER\n');
		elif line.startswith('(<infill>'):
			if (self.bridgeLayer):
				self.output.write(';TYPE:BRIDGE%s' % (self.bridgeFan));
			elif (self.layerNr > self.fanLayer):
				self.output.write(';TYPE:FILL%s' % (self.fillFan));
			else:
				self.output.write(';TYPE:FILL\n');
		elif line.startswith('(<alteration>'):
			self.output.write(';TYPE:CUSTOM\n');
			self.parsingAlteration = True
		elif line.startswith('(</alteration>)'):
			self.parsingAlteration = False
		elif line.startswith('(<supportLayer>'):
			if (self.layerNr > self.fanLayer):
				self.output.write(';TYPE:SUPPORT%s' % (self.supportFan));
			else:
				self.output.write(';TYPE:SUPPORT\n');
