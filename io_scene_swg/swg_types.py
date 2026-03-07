# MIT License
#
# Copyright (c) 2022 Nick Rafalski
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from audioop import cross
import math
from re import I
from sys import maxsize
from xml.dom import minidom
from . import support
from . import nsg_iff
from . import palette_argb
from . import vertex_buffer_format
from . import extents
import mathutils
from mathutils import Vector

SWG_ROOT=None

class SktFile(object):
	__slots__ = (
		'path', 
		'joint_count', 
		'joint_names', 
		'joint_parents', 
		'joint_pre_rotations', 
		'joint_post_rotations', 
		'joint_translations',
		'joint_bind_rotations',
		'joint_rotation_order'
		)
	
	def __init__(self, path):
		self.path = path
		self.joint_count = 0
		self.joint_names = None
		self.joint_parents = None
		self.joint_pre_rotations = None
		self.joint_post_rotations = None
		self.joint_translations = None
		self.joint_bind_rotations = None
		self.joint_rotation_order = None

	def __str__(self):
		return f"{self.path}"
		
	def __repr__(self):
		return self.__str__()
			
	def load(self, sktm_id = 0):
		iff = nsg_iff.IFF(filename=self.path)
		iff.enterForm("SLOD")
		version=iff.getCurrentName()
		if version in ['0000']:
			iff.enterForm(version)
			iff.enterChunk("INFO")
			sktm_ct = iff.read_int16()
			iff.exitChunk("INFO")

			# Invalid skeleton ID
			if sktm_id >= sktm_ct or sktm_id < 0:
				return False
			
			# Loop through SKTMs to find the one we're looking for
			iff.enterForm("SKTM")
			for i in range(sktm_id):
				iff.exitForm("SKTM")
				iff.enterForm("SKTM")
			
			sktm_version=iff.getCurrentName()
			if sktm_version in ['0002']:
				iff.enterAnyForm()
				iff.enterChunk("INFO")
				iff.exitChunk("INFO")
				iff.enterChunk("NAME")
				if not self.joint_names:
					self.joint_names = []
				while not iff.atEndOfForm():
					self.joint_names.append(iff.read_string().lower())
					self.joint_count += 1
				iff.exitChunk("NAME")
				iff.enterChunk("PRNT")
				if not self.joint_parents:
					self.joint_parents = []
				while not iff.atEndOfForm():
					self.joint_parents.append(iff.read_int32())
				iff.exitChunk("PRNT")
				iff.enterChunk("RPRE")
				if not self.joint_pre_rotations:
					self.joint_pre_rotations = []
				while not iff.atEndOfForm():
					self.joint_pre_rotations.append(iff.read_vector4())
				iff.exitChunk("RPRE")
				iff.enterChunk("RPST")
				if not self.joint_post_rotations:
					self.joint_post_rotations = []
				while not iff.atEndOfForm():
					self.joint_post_rotations.append(iff.read_vector4())
				iff.exitChunk("RPST")
				iff.enterChunk("BPTR")
				if not self.joint_translations:
					self.joint_translations = []
				while not iff.atEndOfForm():
					self.joint_translations.append(iff.read_vector3())
				iff.exitChunk("BPTR")
				iff.enterChunk("BPRO")
				if not self.joint_bind_rotations:
					self.joint_bind_rotations = []
				while not iff.atEndOfForm():
					self.joint_bind_rotations.append(iff.read_vector4())
				iff.exitChunk("BPRO")
				iff.enterChunk("JROR")
				if not self.joint_rotation_order:
					self.joint_rotation_order = []
				while not iff.atEndOfForm():
					self.joint_rotation_order.append(iff.read_int32())
				iff.exitChunk("JROR")
				iff.exitForm()

				return True

			else:
				print(f"ERROR: Unsupported SKTM Version: {self.path} Version: {sktm_version}")
				return False
		else:
			print(f"ERROR: Unsupported SLOD Version: {self.path} Version: {version}")
			return False

class LmgFile(object):
	__slots__ = ('path', 'mgns')
	def __init__(self, path, mgns):
		self.path = path
		self.mgns = mgns

	def write(self):
		iff = nsg_iff.IFF(initial_size=512000)	  
		iff.insertForm("MLOD")
		iff.insertForm("0000")

		iff.insertChunk("INFO")
		iff.insert_int16(len(self.mgns))
		iff.exitChunk("INFO")
		for mgn in self.mgns:
			iff.insertChunk("NAME")		
			iff.insertChunkString("appearance/mesh/" + mgn + ".mgn")
			iff.exitChunk("NAME")

		iff.write(self.path)

class SatFile(object):
	__slots__ = ('path', 'mgns', 'skeletons')
	def __init__(self, path, mgns, skeletons):
		self.path = path
		self.mgns = mgns
		self.skeletons = skeletons

	def write(self):
		iff = nsg_iff.IFF(initial_size=512000)	  
		iff.insertForm("SMAT")
		iff.insertForm("0003")

		iff.insertChunk("INFO")
		iff.insert_int32(len(self.mgns))
		iff.insert_int32(len(self.skeletons))
		iff.insert_bool(False)
		iff.exitChunk("INFO")
		
		iff.insertChunk("MSGN")
		iff.insertChunkString("appearance/mesh/" + self.path.split('\\')[-1].split('.')[0] + ".lmg")
		iff.exitChunk("MSGN")
		
		iff.insertChunk("SKTI")
		for skel in self.skeletons:			
			iff.insertChunkString(skel)			
			iff.insertChunkString("")
		iff.exitChunk("SKTI")
		iff.write(self.path)

class AptFile(object):
	__slots__ = ('filename', 'reference')
	def __init__(self, filename, reference = ""):
		self.filename = filename
		self.reference = reference

	def write(self):
		iff = nsg_iff.IFF(initial_size=512000)	  
		iff.insertForm("APT ")
		iff.insertForm("0000")
		iff.insertChunk("NAME")
		iff.insertChunkString(self.reference)
		iff.write(self.filename)

	def load(self):
		print(f"Loading apt from {self.filename}. Reference currently: {self.reference}")
		iff = nsg_iff.IFF(filename=self.filename)
		iff.enterForm("APT ")
		iff.enterAnyForm()
		iff.enterChunk("NAME")
		self.reference = iff.read_string()

	def get_reference_fullpath(self, root):		 
		global SWG_ROOT
		print(f"Apt {self.filename} looking for reference: {self.reference}")
		if self.reference != "":
			return support.find_file(self.reference, root)
		else:
			return None

class PathGraphNode(object):
	typeEnum=['CellPortal','CellWaypoint','CellPOI','BuildingEntrance','BuildingCell','BuildingPortal','CityBuildingEntrance','CityWaypoint','CityPOI','CityBuilding','CityEntrance','BuildingCellPart','Invalid']
	def __init__(self):
		self.position = []
		self.type = 12 #Invalid
		self.radius = 1
		self.index = -1
		self.id = -1
		self.key = -1

	def typeStr(type):
		return PathGraphNode.typeEnum[type]

class PathGraphEdge(object):
	def __init__(self):
		self.indexA = -1
		self.indexB = -1
		self.widthRight = 0
		self.widthLeft = 0

class PathGraph(object):
	__slots__ = ('nodes', 'edges', 'pathGraphType')
	def __init__(self):
		self.nodes = []
		self.edges = []
		self.pathGraphType = 0

	def load(self, iff):
		iff.enterForm("PGRF")
		version = iff.getCurrentName()
		print(f"PGRF version: {version}")
		if version in ["0001"]:
			iff.enterForm(version)
			iff.enterChunk("META")
			self.pathGraphType = iff.read_int32()
			iff.exitChunk("META")

			iff.enterChunk("PNOD")
			count = iff.read_int32()
			print(f"PGRF node count {count}")
			while not iff.atEndOfForm():
				node = PathGraphNode()
				node.index = iff.read_int32()
				node.id = iff.read_int32()
				node.key = iff.read_int32()
				node.type = iff.read_int32()
				node.position = iff.read_vector3()
				node.radius = iff.read_float()
				self.nodes.append(node)
			iff.exitChunk("PNOD")

			iff.enterChunk("PEDG")
			count = iff.read_int32()
			while not iff.atEndOfForm():
				edge = PathGraphEdge()
				edge.indexA = iff.read_int32()
				edge.indexB = iff.read_int32()
				edge.widthRight = iff.read_float()
				edge.widthLeft = iff.read_float()
				self.edges.append(edge)
			iff.exitChunk("PEDG")

			iff.exitForm(version)
		else:
			print(f"Error! PGRF version {version} not supported!")
		iff.exitForm("PGRF")


	def write(self, iff):
		iff.insertForm("PGRF")
		iff.insertForm("0001")
		iff.insertChunk("META")
		iff.insert_int32(3)
		iff.exitChunk("META")
		
		iff.insertChunk("PNOD")
		iff.insert_int32(len(self.nodes))
		for node in self.nodes:
			iff.insert_int32(node.index)
			iff.insert_int32(node.id)
			iff.insert_int32(node.key)			
			iff.insert_int32(node.type)
			iff.insertFloatVector3(node.position)
			iff.insertFloat(node.radius)
		iff.exitChunk("PNOD")
		
		iff.insertChunk("PEDG")
		iff.insert_int32(len(self.edges))
		for edge in self.edges:
			iff.insert_int32(edge.indexA)
			iff.insert_int32(edge.indexB)
			iff.insertFloat(edge.widthRight)
			iff.insertFloat(edge.widthLeft)
		iff.exitChunk("PEDG")

		edgeCounts = [0]*len(self.nodes)
		edgeStarts = [-1]*len(self.nodes)
		for i, edge in enumerate(self.edges):
			edgeCounts[edge.indexA] += 1

			if edgeStarts[edge.indexA] == -1:
				edgeStarts[edge.indexA] = i

		iff.insertChunk("ECNT")
		iff.insert_int32(len(edgeCounts))
		for ec in edgeCounts:
			iff.insert_int32(ec)
		iff.exitChunk("ECNT")

		iff.insertChunk("ESTR")
		iff.insert_int32(len(edgeStarts))
		for es in edgeStarts:
			iff.insert_int32(es)
		iff.exitChunk("ESTR")

		iff.exitForm("0001")
		iff.exitForm("PGRF")

class Portal(object):
	__slots__ = ('verts','tris')
	def __init__(self, verts, tris):
		self.verts = verts
		self.tris = tris

class PortalData(object):
	__slots__ = ('id', 'clockwise', 'passable', 'connecting_cell', 'doorstyle', 'doorhardpoint')
	def __init__(self, id, clockwise, passable, connecting_cell, doorstyle, doorhardpoint):
		self.id = id
		self.clockwise = clockwise
		self.passable = passable
		self.connecting_cell = connecting_cell
		self.doorstyle = doorstyle
		self.doorhardpoint = doorhardpoint

class Cell(object):
	__slots__ = ('name', 'can_see_parent', 'portals', 'appearance_file', 'floor_file', 'collision', 'lights')
	def __init__(self, name, can_see_parent, portals, appearance_file, floor_file, collision, lights):
		self.name = name
		self.can_see_parent = can_see_parent
		self.portals = portals
		self.appearance_file = appearance_file
		self.floor_file = floor_file
		self.collision = collision
		self.lights = lights

class Light(object):
	def __init__(self, lightType, intensity, diffuse_color, specular_color, transform, constant_att, linear_att, quad_att):
		self.lightType = lightType
		self.intensity = intensity
		self.diffuse_color = diffuse_color
		self.specular_color = specular_color
		self.transform = transform
		self.constant_att = constant_att
		self.linear_att = linear_att
		self.quad_att = quad_att

class PobFile(object):
	__slots__ = ('filename', 'portals', 'cells', 'pathGraph', 'crc', 'ship')
	def __init__(self, filename):
		self.filename = filename
		self.portals = []
		self.cells = []
		self.pathGraph = None
		self.crc = None
		self.ship = False

	def write(self, fullpath):
		iff = nsg_iff.IFF(initial_size=512000)	  
		iff.insertForm("PRTO")
		iff.insertForm("0004")
		iff.insertChunk("DATA")
		iff.insert_int32(len(self.portals))
		iff.insert_int32(len(self.cells))
		iff.exitChunk("DATA")

		iff.insertForm("PRTS")
		for portal in self.portals:
			idtl = IndexedTriangleList()
			idtl.verts = portal.verts
			idtl.indexes = portal.tris
			idtl.write(iff)
		iff.exitForm("PRTS")

		iff.insertForm("CELS")
		for cell_id, cell in enumerate(self.cells):
			print(f"Writing out cell {cell.appearance_file}..")
			iff.insertForm("CELL")
			iff.insertForm("0005")
			iff.insertChunk("DATA")
			iff.insert_int32(len(cell.portals))
			iff.insert_bool(cell.can_see_parent)
			iff.insertChunkString(cell.name)
			iff.insertChunkString(cell.appearance_file)
			iff.insert_bool(cell.floor_file != None)
			if cell.floor_file != None:
				iff.insertChunkString(cell.floor_file)
			iff.exitChunk("DATA")

			extents.Extents.write(cell.collision, iff)

			for portal in cell.portals:
				iff.insertForm("PRTL")
				iff.insertChunk("0005")
				if cell_id > 0:
					iff.insert_bool(False)
				else: # Hacky way to do this but only ships seem to set r0 portals to disabled
					iff.insert_bool(self.ship)
				iff.insert_bool(portal.passable)
				iff.insert_int32(portal.id)
				
				iff.insert_bool(portal.clockwise)
				iff.insert_int32(portal.connecting_cell)

				hasHp = portal.doorstyle != None
				iff.insertChunkString(portal.doorstyle if hasHp else "")
				iff.insert_bool(hasHp)
				hpnt = portal.doorhardpoint if hasHp else [1,0,0,0, 0,1,0,0, 0,0,1,0]
				iff.insertFloat(hpnt[0])
				iff.insertFloat(hpnt[1])
				iff.insertFloat(hpnt[2])
				iff.insertFloat(hpnt[3])
				iff.insertFloat(hpnt[4])
				iff.insertFloat(hpnt[5])
				iff.insertFloat(hpnt[6])
				iff.insertFloat(hpnt[7])
				iff.insertFloat(hpnt[8])
				iff.insertFloat(hpnt[9])
				iff.insertFloat(hpnt[10])
				iff.insertFloat(hpnt[11])

				iff.exitChunk("0005")
				iff.exitForm("PRTL")

			iff.insertChunk("LGHT")
			iff.insert_int32(len(cell.lights))
			for light in cell.lights:
				iff.insert_int8(light.lightType)
				iff.insertFloat(light.intensity)
				iff.insertFloat(light.diffuse_color[0] * light.intensity)
				iff.insertFloat(light.diffuse_color[1] * light.intensity)
				iff.insertFloat(light.diffuse_color[2] * light.intensity)
				
				iff.insertFloat(light.intensity)
				iff.insertFloat(light.specular_color[0] * light.intensity)
				iff.insertFloat(light.specular_color[1] * light.intensity)
				iff.insertFloat(light.specular_color[2] * light.intensity)
				iff.insertFloat(light.transform[0])
				iff.insertFloat(light.transform[1])
				iff.insertFloat(light.transform[2])
				iff.insertFloat(light.transform[3])
				iff.insertFloat(light.transform[4])
				iff.insertFloat(light.transform[5])
				iff.insertFloat(light.transform[6])
				iff.insertFloat(light.transform[7])
				iff.insertFloat(light.transform[8])
				iff.insertFloat(light.transform[9])
				iff.insertFloat(light.transform[10])
				iff.insertFloat(light.transform[11])

				iff.insertFloat(light.constant_att)
				iff.insertFloat(light.linear_att)
				iff.insertFloat(light.quad_att)

			iff.exitChunk("LGHT")

			iff.exitForm("0005")
			iff.exitForm("CELL")
		iff.exitForm("CELS")

		self.pathGraph.write(iff)

		iff.insertChunk("CRC ")
		if self.crc == None:
			iff.insert_int32(iff.calculate())
		else:
			iff.insert_int32(self.crc)
		iff.exitChunk("CRC ")

		iff.exitForm("0004")
		iff.exitForm("PRTO")
		iff.write(fullpath)

	def load(self):
		print(f"Loading pob from {self.filename}")
		iff = nsg_iff.IFF(filename=self.filename)
		iff.enterForm("PRTO")
		version = iff.getCurrentName()
		if version in ["0004", "0003"]:
			iff.enterForm(version)
			iff.enterChunk("DATA")
			num_portals = iff.read_int32()
			num_cells = iff.read_int32()
			iff.exitChunk("DATA")

			if version == "0003":
				self.load_0003_prtl(iff, num_portals)
			elif version == "0004":
				self.load_0004_prtl(iff, num_portals)			

			iff.enterForm("CELS")
			for i in range(0, num_cells):
				iff.enterForm("CELL")
				iff.enterForm("0005")
				iff.enterChunk("DATA")
				num_portals = iff.read_int32()
				can_see_parent = iff.read_bool8()
				name = iff.read_string()
				appearance = iff.read_string()
				floor=None
				if iff.read_bool8():
					floor = iff.read_string()
				iff.exitChunk("DATA")

				print(f"CELL {i} collision form: {iff.getCurrentName()}")
				collision = extents.Extents.create(iff)

				portals=[]
				for pi in range(0, num_portals):
					iff.enterForm("PRTL")
					version = iff.getCurrentName()
					if version in ['0004', '0005']:
						iff.enterChunk(version)
						disabled = False

						if version == '0005':
							disabled = iff.read_bool8()
							# Hacky way to figure out if this is a ship; only ships seem to disable the r0 portals
							if not self.ship:
								self.ship = disabled
						
						passable = iff.read_bool8()
						portal_id = iff.read_int32()
						clockwise = iff.read_bool8()
						leads_to_room = iff.read_int32()
						door_style = iff.read_string()
						has_door_hardpoint = iff.read_bool8()
						doorhardpoint = None
						if has_door_hardpoint:
							rotXx = iff.read_float()
							rotXy = iff.read_float()
							rotXz = iff.read_float()
							posX = iff.read_float()
							rotYx = iff.read_float()
							rotYy = iff.read_float()
							rotYz = iff.read_float()
							posY = iff.read_float()
							rotZx = iff.read_float()
							rotZy = iff.read_float()
							rotZz = iff.read_float()
							posZ = iff.read_float()
							doorhardpoint = [rotXx, rotXy, rotXz, -posX, rotYx, rotYy, rotYz, posY, rotZx, rotZy, rotZz, posZ]
			
						print(f"[Cell {i} Portal {pi}] Disabled: {disabled} Passable: {passable} portal_id: {portal_id} clockwise: {clockwise}, leads_to_room: {leads_to_room} door_style: '{door_style}' has_door_hardpoint: {has_door_hardpoint}")
						portals.append(PortalData(portal_id, clockwise, passable, leads_to_room, None if door_style == "" else door_style, doorhardpoint))
						iff.exitChunk(version)
					else:
						print(f"Cell {i}, unhandled PRTL version {version}")
						return
					iff.exitForm("PRTL")

				iff.enterChunk("LGHT")
				count = iff.read_int32()
				lights = []
				for i in range(0, count):
					lightType = iff.read_int8()

					da = iff.read_float()
					dr = iff.read_float()
					dg = iff.read_float()
					db = iff.read_float()
					
					sa = iff.read_float()
					sr = iff.read_float()
					sg = iff.read_float()
					sb = iff.read_float()

					rotXx = iff.read_float()
					rotXy = iff.read_float()
					rotXz = iff.read_float()
					posX = iff.read_float()

					rotYx = iff.read_float()
					rotYy = iff.read_float()
					rotYz = iff.read_float()
					posY = iff.read_float()

					rotZx = iff.read_float()
					rotZy = iff.read_float()
					rotZz = iff.read_float()
					posZ = iff.read_float()
					transform = [rotXx, rotXy, rotXz, -posX, rotYx, rotYy, rotYz, posY, rotZx, rotZy, rotZz, posZ]

					const_att = iff.read_float()
					linear_att = iff.read_float()
					quad_att = iff.read_float()

					lights.append(Light(lightType, da, [dr,dg,db], [sr,sg,sb], transform, const_att, linear_att, quad_att))

				iff.exitChunk("LGHT")
				iff.exitForm("0005")
				iff.exitForm("CELL") 
				self.cells.append(Cell(name, can_see_parent, portals, appearance, floor, collision, lights))
			iff.exitForm("CELS")

			if iff.getCurrentName() == "PGRF":
				self.pathGraph = PathGraph()
				self.pathGraph.load(iff)

			if iff.getCurrentName() == "CRC ":
				iff.enterChunk("CRC ")
				self.crc = iff.read_int32()
				iff.exitChunk("CRC ")

		else:
			print(f"Unhandled PRTO version: {version}")
			return	 
	
	def load_0004_prtl(self, iff, num_portals):
		iff.enterForm("PRTS")
		for i in range(0, num_portals):
			iff.enterForm("IDTL")
			iff.enterForm("0000")
			verts=[]
			tris=[]

			iff.enterChunk("VERT")
			while not iff.atEndOfForm():
				verts.append(Vector([iff.read_float(), iff.read_float(), iff.read_float()]))
			iff.exitChunk("VERT")
			
			iff.enterChunk("INDX")
			while not iff.atEndOfForm():
				tris.append(Triangle(iff.read_int32(),iff.read_int32(),iff.read_int32()))
			iff.exitChunk("INDX")

			iff.exitForm("0000")
			iff.exitForm("IDTL")

			self.portals.append(Portal(verts,tris))
		print(f"Found Portals: {len(self.portals)}")
		iff.exitForm("PRTS")

	def load_0003_prtl(self, iff, num_portals):
		iff.enterForm("PRTS")
		for i in range(0, num_portals):
			verts=[]
			tris=[]

			iff.enterChunk("PRTL")
			num_verts = iff.read_int32()
			while not iff.atEndOfForm():
				verts.append(Vector([iff.read_float(), iff.read_float(), iff.read_float()]))
			iff.exitChunk("PRTL")

			for i in range(2, num_verts):
				tris.append(Triangle(0, i-1, i))
				print(f"Tri {i}: (0, {i-1}, {i})")

			self.portals.append(Portal(verts,tris))
		print(f"Found Portals: {len(self.portals)}")
		iff.exitForm("PRTS")

class LodFile(object):

	__slots__ = ('path', 'extents', 'mesh','hardpoints','collision','floor', 'lods', 'radar', 'testshape', 'writeshape')
	def __init__(self, path):
		self.path = path
		self.extents = None
		self.mesh = None
		self.collision = None
		self.hardpoints = []
		self.lods = {}
		self.floor = None
		self.radar = None
		self.testshape = None
		self.writeshape = None

	def __str__(self):
		return f'Path: {self.path}, Hpts: {str(len(self.hardpoints))} Lods: {str(self.lods)}'

	def __repr__(self):
		return self.__str__()

	def load(self, path):
		iff = nsg_iff.IFF(filename=path)
		#print(f"Name: {iff.getCurrentName()} Length: {iff.getCurrentLength()}")
		
		top = iff.getCurrentName()
		if top != "DTLA":
			print(f"Not an LOD file. First form: {top} should be DTLA!")
			return False
		else:
			iff.enterForm("DTLA")

		dtla_version = iff.getCurrentName()
		if dtla_version not in ["0007", "0008", "0005"]:
			print(f'Unsupported DTLA version: {dtla_version}')
			return False
		else: 
			iff.enterForm(dtla_version)

		iff.enterForm("APPR")

		version = iff.getCurrentName()
		if version not in ["0003"]:
			print(f'Unsupported APPR version: {version}')
			return False
		else: 
			iff.enterForm(version)

		self.extents = extents.Extents.create(iff)
		self.collision = extents.Extents.create(iff)

		# Hardpoints
		iff.enterForm("HPTS", True, False)
		while not iff.atEndOfForm():
			iff.enterChunk("HPNT", True)
			rotXx = iff.read_float()
			rotXy = iff.read_float()
			rotXz = iff.read_float()
			posX = iff.read_float()
			rotYx = iff.read_float()
			rotYy = iff.read_float()
			rotYz = iff.read_float()
			posY = iff.read_float()
			rotZx = iff.read_float()
			rotZy = iff.read_float()
			rotZz = iff.read_float()
			posZ = iff.read_float()
			hpntName = iff.read_string()
			self.hardpoints.append([rotXx, rotXy, rotXz, -posX, rotYx, rotYy, rotYz, posY, rotZx, rotZy, rotZz, posZ, hpntName])
			iff.exitChunk("HPNT")
		iff.exitForm("HPTS")

		if iff.enterForm("FLOR", True):
			if iff.enterChunk("DATA", True):
				if iff.read_bool8() == True:
					self.floor = iff.read_string()
				iff.exitChunk("DATA")
			iff.exitForm("FLOR")
		
		iff.exitForm() # APPR Version
		iff.exitForm() # APPR

		# PIVT
		if iff.getCurrentName() == "PIVT":
			iff.enterChunk("PIVT")
			hasPivot = iff.read_bool8()
			iff.exitChunk("PIVT")
		
		print(f"Current: {iff.getCurrentName()} size {iff.getCurrentLength()}")
		iff.enterChunk("INFO")
		while not iff.atEndOfForm():
			id=iff.read_uint32()
			near=iff.read_float()
			far=iff.read_float()
			self.lods[id]=[near,far]
		iff.exitChunk("INFO")

		iff.enterForm("DATA")
		while not iff.atEndOfForm():
			iff.enterChunk("CHLD")
			ind = iff.read_uint32()
			self.lods[ind].append(iff.read_string())
			iff.exitChunk("CHLD")
		iff.exitForm("DATA")


		if iff.getCurrentName() == "RADR":
			iff.enterForm("RADR")
			iff.enterChunk("INFO")
			test = (iff.read_int32() != 0)
			iff.exitChunk("INFO")
			if(test):
				idtl = IndexedTriangleList()
				idtl.load(iff)
				self.radar = idtl
			iff.exitForm("RADR")


		if iff.getCurrentName() == "TEST":
			iff.enterForm("TEST")
			iff.enterChunk("INFO")
			test = (iff.read_int32() != 0)
			iff.exitChunk("INFO")
			if(test):
				idtl = IndexedTriangleList()
				idtl.load(iff)
				self.testshape = idtl
			iff.exitForm("TEST")


		if iff.getCurrentName() == "WRIT":
			iff.enterForm("WRIT")
			iff.enterChunk("INFO")
			test = (iff.read_int32() != 0)
			iff.exitChunk("INFO")
			if(test):
				idtl = IndexedTriangleList()
				idtl.load(iff)
				self.writeshape = idtl
			iff.exitForm("WRIT")

		return True

	def write(self, fullpath):
		iff = nsg_iff.IFF(initial_size=512000)	  
		iff.insertForm("DTLA")
		iff.insertForm("0008")
		
		iff.insertForm("APPR")
		iff.insertForm("0003")

		self.extents.write(iff)

		extents.Extents.write(self.collision, iff)

		iff.insertForm("HPTS")
		if len(self.hardpoints) > 0:
			for hpnt in self.hardpoints:
				iff.insertChunk("HPNT")
				iff.insertFloat(hpnt[0])
				iff.insertFloat(hpnt[1])
				iff.insertFloat(hpnt[2])
				iff.insertFloat(hpnt[3]) #x pos
				iff.insertFloat(hpnt[4])
				iff.insertFloat(hpnt[5])
				iff.insertFloat(hpnt[6])
				iff.insertFloat(hpnt[7]) #y pos
				iff.insertFloat(hpnt[8])
				iff.insertFloat(hpnt[9])
				iff.insertFloat(hpnt[10])
				iff.insertFloat(hpnt[11]) #z pos
				iff.insertChunkString(hpnt[12]) #hpnt name
				iff.exitChunk("HPNT")
		iff.exitForm()


		iff.insertForm("FLOR")
		iff.insertChunk("DATA")
		iff.insert_bool(self.floor != None)
		if self.floor != None:
			iff.insertChunkString(self.floor)
		iff.exitChunk("DATA")
		iff.exitForm("FLOR")

		iff.exitForm("0003")
		iff.exitForm("APPR")

		iff.insertChunk("PIVT")
		iff.insert_bool(False)
		iff.exitChunk("PIVT")

		iff.insertChunk("INFO")
		for id, lod in self.lods.items():
			iff.insert_int32(id)
			iff.insertFloat(lod[0])
			iff.insertFloat(lod[1])
		iff.exitChunk("INFO")

		iff.insertForm("DATA")
		for id, lod in self.lods.items():			
			iff.insertChunk("CHLD")
			iff.insert_int32(id)
			iff.insertChunkString(lod[2])
			iff.exitChunk("CHLD")
		iff.exitForm("DATA")

		iff.insertForm("RADR")
		iff.insertChunk("INFO")
		iff.insert_int32(self.radar != None)		
		iff.exitChunk("INFO")
		if self.radar != None:
			self.radar.write(iff)
		iff.exitForm("RADR")

		iff.insertForm("TEST")
		iff.insertChunk("INFO")
		iff.insert_int32(self.testshape != None)		
		iff.exitChunk("INFO")
		if self.testshape != None:
			self.testshape.write(iff)
		iff.exitForm("TEST")

		iff.insertForm("WRIT")
		iff.insertChunk("INFO")
		iff.insert_int32(self.writeshape != None)		
		iff.exitChunk("INFO")
		if self.writeshape != None:
			self.writeshape.write(iff)
		iff.exitForm("WRIT")
		
		iff.write(fullpath)	

class IndexedTriangleList(object):
	__slots__ = ('verts', 'indexes')
	def __init__(self):
		self.verts = []
		self.indexes = []

	def load(self, iff):
		iff.enterForm("IDTL")
		version = iff.getCurrentName()
		if version not in ["0000"]:
			print(f"Unsupported IDTL version: {version}")
			iff.exitForm("IDTL")
			return False
		else:
			iff.enterForm(version)
			
			iff.enterChunk("VERT")
			while not iff.atEndOfForm():
				self.verts.append(iff.read_vector3())
			iff.exitChunk("VERT")

			iff.enterChunk("INDX")
			while not iff.atEndOfForm():
				self.indexes.append([iff.read_int32(),iff.read_int32(),iff.read_int32()])
			iff.exitChunk("INDX")
			iff.exitForm(version)
			iff.exitForm("IDTL")
			return True

	def write(self, iff):
		iff.insertForm("IDTL")
		iff.insertForm("0000")

		iff.insertChunk("VERT")
		for v in self.verts:
			iff.insertFloatVector3(v)
		iff.exitChunk("VERT")

		iff.insertChunk("INDX")
		for i in self.indexes:
			iff.insertInt32Vector3(i)
		iff.exitChunk("INDX")

		iff.exitForm("0000")
		iff.exitForm("IDTL")
		
class FloorTri(object):
	Uncrossable = 0
	Crossable = 1
	WallBase = 2
	WallTop = 3
	__slots__ = ('corner1','corner2','corner3','index','nindex1','nindex2','nindex3','normal','edgeType1','edgeType2','edgeType3','fallthrough','partTag','portalId1','portalId2','portalId3')
	def __init__(self):
		self.corner1 = 0
		self.corner2 = 0
		self.corner3 = 0
		
		self.index = 0
		
		self.nindex1 = -1
		self.nindex2 = -1
		self.nindex3 = -1
		
		self.normal = [0,0,0]
		
		self.edgeType1 = FloorTri.Uncrossable
		self.edgeType2 = FloorTri.Uncrossable
		self.edgeType3 = FloorTri.Uncrossable
		
		self.fallthrough = False
		
		self.partTag = 0
		
		self.portalId1 = -1
		self.portalId2 = -1
		self.portalId3 = -1

	def read_0002(self, iff):
		self.corner1 = iff.read_int32()
		self.corner2 = iff.read_int32()
		self.corner3 = iff.read_int32()

		self.index = iff.read_int32()

		self.nindex1 = iff.read_int32()
		self.nindex2 = iff.read_int32()
		self.nindex3 = iff.read_int32()

		self.normal = iff.read_vector3()

		self.edgeType1 = iff.read_uint8()
		self.edgeType2 = iff.read_uint8()
		self.edgeType3 = iff.read_uint8()

		#print(f" edges: {self.edgeType1}, {self.edgeType2}, {self.edgeType3}")

		self.fallthrough = iff.read_bool8()

		self.partTag = iff.read_int32()

		self.portalId1 = iff.read_int32()
		self.portalId2 = iff.read_int32()
		self.portalId3 = iff.read_int32()

	def write_0002(self, iff):
		iff.insert_int32(self.corner1)
		iff.insert_int32(self.corner2)
		iff.insert_int32(self.corner3)

		iff.insert_int32(self.index)

		iff.insert_int32(self.nindex1)
		iff.insert_int32(self.nindex2)
		iff.insert_int32(self.nindex3)

		iff.insertFloatVector3(self.normal)

		iff.insert_int8(self.edgeType1)
		iff.insert_int8(self.edgeType2)
		iff.insert_int8(self.edgeType3)

		iff.insert_bool(self.fallthrough)

		iff.insert_int32(self.partTag)

		iff.insert_int32(self.portalId1)
		iff.insert_int32(self.portalId2)
		iff.insert_int32(self.portalId3)

class PathEdge(object):
	__slots__ = ('tri','edge','crossable')
	def __init__(self, tri, edge, crossable):
		self.tri = tri
		self.edge = edge
		self.crossable = crossable
	
	def write(self, iff):
		iff.insert_int32(self.tri)
		iff.insert_int32(self.edge)
		iff.insert_bool(self.crossable)

class FloorFile(object):

	__slots__ = ('path', 'verts', 'tris', 'pathGraph')
	def __init__(self, path):
		self.path = path
		self.verts = []
		self.tris = []
		self.pathGraph = None

	def __str__(self):
		return f"Path: {self.path}"

	def __repr__(self):
		return self.__str__()

	def load(self):
		iff = nsg_iff.IFF(filename=self.path)
		iff.enterForm("FLOR")		
		version = iff.getCurrentName()
		if version in ["0006", "0005"]:
			iff.enterForm(version)
			
			iff.enterChunk("VERT")
			vertCount = iff.read_int32()
			while not iff.atEndOfForm():
				pos = iff.read_vector3()
				self.verts.append(pos)
			iff.exitChunk("VERT")

			iff.enterChunk("TRIS")
			triCount = iff.read_int32()
			for i in range(0, triCount):
				#print(f"Tri {i}:")
				f = FloorTri()
				f.read_0002(iff)
				self.tris.append(f)
			iff.exitChunk("TRIS")

			if not iff.atEndOfForm() and iff.getCurrentName() == "BTRE":
				iff.enterForm("BTRE")
				iff.exitForm("BTRE")
			
			if not iff.atEndOfForm() and iff.getCurrentName() == "BEDG":
				iff.enterChunk("BEDG")
				iff.exitChunk("BEDG")
			
			if not iff.atEndOfForm() and iff.getCurrentName() == "PGRF":
				self.pathGraph = PathGraph()
				self.pathGraph.load(iff)

			print(f"Verts: {len(self.verts)} Tris: {len(self.tris)}")
		else:
			print(f"Unhandled FLR version: {version}")
			return False

		return True

	def write(self):
		iff = nsg_iff.IFF(initial_size=512000)
		iff.insertForm("FLOR")
		iff.insertForm("0006")

		iff.insertChunk("VERT")
		iff.insert_int32(len(self.verts))
		for v in self.verts:
			iff.insertFloatVector3(v)
		iff.exitChunk("VERT")

		iff.insertChunk("TRIS")
		iff.insert_int32(len(self.tris))
		for t in self.tris:
			t.write_0002(iff)
		iff.exitChunk("TRIS")

		borderEdges = []
		for index, tri in enumerate(self.tris):
			if tri.nindex1 == -1:
				borderEdges.append(PathEdge(index, 0, (tri.edgeType1 != FloorTri.Uncrossable)))
			if tri.nindex2 == -1:
				borderEdges.append(PathEdge(index, 1, (tri.edgeType2 != FloorTri.Uncrossable)))
			if tri.nindex3 == -1:
				borderEdges.append(PathEdge(index, 2, (tri.edgeType1 != FloorTri.Uncrossable)))
		iff.insertChunk("BEDG")
		iff.insert_int32(len(borderEdges))
		for be in borderEdges:
			be.write(iff)
		iff.exitChunk("BEDG")

		if self.pathGraph != None:
			self.pathGraph.write(iff)

		iff.write(self.path)

	def do_nodes_connect(self, nodeA, nodeB):

		resultA = None
		resultB = None

		# First locate which triangles the nodes are on..
		for tiA, triA in enumerate(self.tris):
			corners = [Vector(self.verts[i]) for i in [triA.corner1, triA.corner2, triA.corner3]]
			pointA = Vector(nodeA.position)
			resultA = mathutils.geometry.intersect_point_tri(pointA, corners[0], corners[1], corners[2])
			if resultA != None:
				distA = (resultA - pointA).length
				#print(f"Node {nodeA.index} at {nodeA.position} is above tri: {ti} with corners ({self.verts[tri.corner1]}, {self.verts[tri.corner2]}, {self.verts[tri.corner3]} Result: {resultA}) Dist: {distA}")
				if resultA > 0.1:
					resultA = None
				else:
					#print(f"Node {nodeA.index} at {nodeA.position} is above tri: {tiA} with corners ({self.verts[triA.corner1]}, {self.verts[triA.corner2]}, {self.verts[triA.corner3]} Result: {resultA}) Dist: {distA}")
					break
		
		for tiB, triB in enumerate(self.tris):
			cornersB = [Vector(self.verts[i]) for i in [triB.corner1, triB.corner2, triB.corner3]]
			pointB = Vector(nodeB.position)
			resultB = mathutils.geometry.intersect_point_tri(pointB, cornersB[0], cornersB[1], cornersB[2])
			if resultB != None:
				distB = (resultB - pointB).length
				#print(f"Node {nodeB.index} at {nodeB.position} is above tri: {ti} with corners ({self.verts[tri.corner1]}, {self.verts[tri.corner2]}, {self.verts[tri.corner3]}) Result: {resultB} Dist: {distB}")
				if distB > 0.1:
					resultB = None
				else:
					#print(f"Node {nodeB.index} at {nodeB.position} is above tri: {tiB} with corners ({self.verts[triB.corner1]}, {self.verts[triB.corner2]}, {self.verts[triB.corner3]}) Result: {resultB} Dist: {distB}")
					break

		if (resultA == None) or (resultB == None):
			#print(f"One of the nodes at {nodeA.position} or {nodeB.position} are't on a floor triangle! Skipping!")
			return False
		else:
			#print(f"NodeA: {nodeA.index} at {nodeA.position} on triangle at {resultA}")
			#print(f"NodeB: {nodeB.index} at {nodeB.position} on triangle at {resultB}")
			pass

		for ti, tri in enumerate(self.tris):
			corners = [Vector(self.verts[i]) for i in [tri.corner1, tri.corner2, tri.corner3]]
			if self.do_lines_intersect(resultA, resultB, corners[0], corners[1]) and (tri.edgeType1 == FloorTri.Uncrossable):
				return False
			if self.do_lines_intersect(resultA, resultB, corners[1], corners[2]) and (tri.edgeType2 == FloorTri.Uncrossable):
				return False
			if self.do_lines_intersect(resultA, resultB, corners[2], corners[0]) and (tri.edgeType3 == FloorTri.Uncrossable):
				return False

		return True

	def do_lines_intersect(self, nA, nB, lA, lB):
		result = mathutils.geometry.intersect_line_line(nA, nB, lA, lB)
		if result != None:
			onPath = FloorFile.isBetween(lA,lB,result[0])
			onEdge = FloorFile.isBetween(nA,nB,result[0])
			return onPath and onEdge
		else:
			return False

	def isBetween(a, b, c):
		crossproduct = (c.y - a.y) * (b.x - a.x) - (c.x - a.x) * (b.y - a.y)
		if abs(crossproduct) > 0.001:
			return False
		distAB = (b - a).length
		distAC = (c - a).length
		distBC = (c - b).length
		return ((distAC < distAB) and (distBC < distAB))


	def make_waypoint_connections(self):
		if self.pathGraph == None:
			print(f"Error! Asked to make waypoint connecitons without first assigning pathGraph")
			return

		for node in self.pathGraph.nodes:
			if node.type == 1:
				for node2 in self.pathGraph.nodes:
					if node2.type == 1 and (node != node2):
						if self.do_nodes_connect(node, node2):
							#print(f"Nodes {node.position} and {node2.position} are connected!")						 
							edge = PathGraphEdge()
							edge.indexA = node.index
							edge.indexB = node2.index
							self.pathGraph.edges.append(edge)	  
		

	def add_portal_nodes(self, globalPortalIndecies):
		if self.pathGraph == None:
			print(f"Error! Asked to add_portal_nodes without first assigning pathGraph")
			return

		starting_size = len(self.pathGraph.nodes)
		last_index=-1

		if starting_size > 0:
			last_index = self.pathGraph.nodes[-1].index

		portalIdsAdded=set()
		for tri in self.tris:
			A = None
			B = None
			C = None
			pid = None
			if tri.portalId1 != -1:
				pid = globalPortalIndecies[tri.portalId1]
				A = Vector(self.verts[tri.corner1])
				B = Vector(self.verts[tri.corner2])
			elif tri.portalId2 != -1:
				pid = globalPortalIndecies[tri.portalId2]
				A = Vector(self.verts[tri.corner2])
				B = Vector(self.verts[tri.corner3])
			elif tri.portalId3 != -1:
				pid = globalPortalIndecies[tri.portalId3]
				A = Vector(self.verts[tri.corner3])
				B = Vector(self.verts[tri.corner1])
			if pid != None:
				C = A + ((B-A) / 2.0)
				if pid not in portalIdsAdded:
					last_index += 1
					node = PathGraphNode()
					node.type = 0
					node.index = last_index
					node.key = pid
					node.position = C
					node.radius = 0
					self.pathGraph.nodes.append(node)
					portalIdsAdded.add(pid)

		print(f"Added {len(portalIdsAdded)} portal nodes. Now at {len(self.pathGraph.nodes)}")


	def add_portal_edges(self):
		if self.pathGraph == None:
			print(f"Error! Asked to add_portal_edges without first assigning pathGraph")
			return

		for ni1, node1 in enumerate(self.pathGraph.nodes):
			if node1.type != 0: 
				continue

			minId = -1
			minDist = maxsize

			for ni2, node2 in enumerate(self.pathGraph.nodes):
				if node2.type == 0 or (node1 == node2): 
					continue

				connectable = self.do_nodes_connect(node1, node2)
				dist = (Vector(node2.position) - Vector(node1.position)).length
				#print(f"Comparing node {node1.index} to node {node2.index} Connectable: {connectable} dist: {dist}")
				if connectable and (dist < minDist):
					minDist = dist
					minId = node2.index
					#print(f"   {node2.index} is better!")
				else:
					#print(f"   {node2.index} is not better")
					pass

			if minId != -1:
				edge = PathGraphEdge()
				edge.indexA = node1.index
				edge.indexB = minId
				self.pathGraph.edges.append(edge)

				edge2 = PathGraphEdge()
				edge2.indexA = minId
				edge2.indexB = node1.index
				self.pathGraph.edges.append(edge2)

				#print(f"Adding portal connecting edge from {node1.index} to {minId}!")
				

	def prune_redundant_edges(self):
		edgesToRemove=set()
		for edge1 in self.pathGraph.edges:
			for edge2 in self.pathGraph.edges:

				AA = edge1.indexA
				AB = edge1.indexB
				BA = edge2.indexA
				BB = edge2.indexB

				if ((AA == BA) and (AB == BB)):
					continue
				if ((AA == BB) and (AB == BA)):
					continue

				if(AA == BA):
					A = Vector(self.pathGraph.nodes[AA].position)
					B = Vector(self.pathGraph.nodes[AB].position)
					C = Vector(self.pathGraph.nodes[BB].position)
				elif(AA == BB):
					A = Vector(self.pathGraph.nodes[AA].position)
					B = Vector(self.pathGraph.nodes[AB].position)
					C = Vector(self.pathGraph.nodes[BA].position)
				elif(AB == BA):
					A = Vector(self.pathGraph.nodes[AB].position)
					B = Vector(self.pathGraph.nodes[AA].position)
					C = Vector(self.pathGraph.nodes[BB].position)
				elif(AB == BB):
					A = Vector(self.pathGraph.nodes[AB].position)
					B = Vector(self.pathGraph.nodes[AA].position)
					C = Vector(self.pathGraph.nodes[BA].position)
				else:				
					continue

				dA = (B-A).normalized()
				dB = (C-A).normalized()
				if(support.angle_between_unnormalized(dA, dB) < ((20.0 / 360.0) * (2.0 * math.pi))):
					if((B-A).length > (C-A).length):
						edgesToRemove.add(edge1)
					else:
						edgesToRemove.add(edge2)
		before=len(self.pathGraph.edges)
		for e in edgesToRemove:
			if e in self.pathGraph.edges:
				self.pathGraph.edges.remove(e)		
		print(f"Edges before: {before} but removed: {len(edgesToRemove)}. Now: {len(self.pathGraph.edges)}")

class MgnHardpoint(object):
	__slots__ = ('name', 'parent', 'orientation', 'position')
	def __init__(self, name, parent, orientation, position):
		self.name = name
		self.parent = parent
		self.orientation = orientation
		self.position = position
	def __str__(self):
		return f'Name: {self.name}, Parent: {self.parent} Orientation: {self.orientation}, Position: {self.position}'

	def __repr__(self):
		return self.__str__()

class SWGVertex(object):
	__slots = ('pos', 'normal', 'color', 'texs')
	def __init__(self):
		self.texs = []
		self.pos = None
		self.normal = None
		self.color0 = None
		self.color1 = None

	def __str__(self):
		return f'P: {self.pos} N: {self.normal} UV0: {self.texs[0]}'

	def __repr__(self):
		return self.__str__()

class Triangle(object):
	__slots__ = ('p1', 'p2', 'p3')
	def __init__(self, p1 = None, p2 = None, p3 = None):
		self.p1 = p1
		self.p2 = p2
		self.p3 = p3
		
	def __str__(self):
		return f"[{self.p1}, {self.p2}, {self.p3}]"
	def __repr__(self):
		return self.__str__()

class SWGShader(object):
	__slots__ = ('path', 'root', 'main', 'specular', 'normal', 'compressed_normal', 'envm', 'emission', 'detail', 'hueb', 'effect', 'customizable', 'palette_colors', 'transparent')
	def __init__(self, path, root):
		self.path=path
		self.root=root
		self.main=None
		self.specular=None
		self.normal=None
		self.compressed_normal=None
		self.envm=None
		self.emission=None
		self.detail=None
		self.hueb=None
		self.customizable=False
		self.palette_colors={}
		self.transparent=False
		self.effect = None
		self.load()

	def __str__(self):
		return f"[{self.path}, {self.main}, {self.spec}]"
		
	def __repr__(self):
		return self.__str__()

	def stripped_shader_name(self):
		if self.path == "":
			return "defaultappearance"
		else:
			return (support.clean_path(self.path).split('\\')[-1]).split('.')[0]

	def infer_features_from_effect(self):
		if self.effect:
			self.transparent = any([x in self.effect for x in ["alpha", "invis", "water"]])
			
	def load(self):
		iff = nsg_iff.IFF(filename=self.path)
		#print(f"Name: {iff.getCurrentName()} Length: {iff.getCurrentLength()}")
		top_form = iff.getCurrentName()
		if top_form == "CSHD":
			self.customizable = True
			self.load_cshd(iff)
		elif top_form == "SSHT":
			self.customizable = False
			self.load_ssht(iff)
		elif top_form == "SWTS":
			self.customizable = False
			self.load_swts(iff)
		else: 
			print(f"Shader: {self.path} is unsupported shader type: {top_form}. Won't decode!")
			iff.exitForm()

		self.infer_features_from_effect()

	def load_cshd(self, iff):
		iff.enterForm("CSHD")
		version = iff.getCurrentName()
		if version in ["0001"]:
			iff.enterForm(version)
			self.load_ssht(iff)
			# Texture patterns
			if iff.getCurrentName() == "TXTR":
				iff.enterForm("TXTR")
				iff.exitForm("TXTR")
			# Hueable shaders
			if iff.getCurrentName() == "TFAC":
				iff.enterForm("TFAC")
				while not iff.atEndOfForm():
					if iff.getCurrentName() == "PAL ":
						iff.enterChunk("PAL ")
						iff.read_string() # Variable Name
						iff.read_byte() # Variable Private?
						tag = iff.read_tag() # Texture Tag
						pal_path = iff.read_string()
						pal_path = support.find_file(pal_path, self.root)
						print(f"Looking for palette: {pal_path}")
						if pal_path:
							palette = palette_argb.PaletteArgb(pal_path)
							pal_idx = iff.read_int32()
							# The h_color2w_rb shaders use HUEB for both index colors
							# We use the tag instead of the Variable Name because we can't guarantee consistency in variable assignment to texture tags
							if tag in self.palette_colors:
								tag = tag + "2"
							if palette.size > pal_idx:
								self.palette_colors[tag] = palette.colors[pal_idx]
							else:
								self.palette_colors[tag] = [1.0,1.0,1.0]
						iff.exitChunk("PAL ")
				iff.exitForm("TFAC")
			iff.exitForm(version)
		else:			
			print(f"{iff.filename}: unsupported CSHD Version: {version}!")
		iff.exitForm("CSHD")

	def load_ssht(self, iff):
		iff.enterForm("SSHT")
		version = iff.getCurrentName()
		if version in ["0000", "0001"]:
			iff.enterForm(version)
			if iff.getCurrentName() == "NAME":
				iff.enterChunk("NAME")
				self.effect = iff.read_string()
				iff.exitChunk("NAME")

			iff.enterForm("MATS")
			iff.exitForm("MATS")

			if iff.getCurrentName() == "TXMS":
				iff.enterForm("TXMS")
				#count = 0
				while not iff.atEndOfForm():
					#count += 1
					iff.enterForm("TXM ")
					iff.enterAnyForm() # version
					iff.enterChunk("DATA")
					tag = iff.read_string()[::-1] # reverse tag
					iff.exitChunk("DATA")
					iff.enterChunk("NAME")
					texture= iff.read_string()
					iff.exitChunk("NAME")
					iff.exitForm()
					iff.exitForm("TXM ")
					#print(f"Tag: {tag}: {texture}")

					if tag == "MAIN":
						self.main = texture
					elif tag == "SPEC":
						self.specular = texture
					elif tag == "CNRM":
						self.compressed_normal = texture
					elif tag == "NRML":
						self.normal = texture
					elif tag == "ENVM":
						self.envm = texture
					elif tag == "EMIS":
						self.emission = texture
					elif tag == "DETA":
						self.detail = texture
					elif tag == "HUEB":
						self.hueb = texture
				
				iff.exitForm("TXMS")

			if iff.getCurrentName() == "TCSS":
				iff.enterForm("TCSS")
				iff.exitForm("TCSS")

			if iff.getCurrentName() == "TFNS":
				iff.enterForm("TFNS")
				iff.exitForm("TFNS")

			if iff.getCurrentName() == "ARVS":
				iff.enterForm("ARVS")
				iff.exitForm("ARVS")

			if iff.getCurrentName() == "SRVS":
				iff.enterForm("SRVS")
				iff.exitForm("SRVS")

			if iff.getCurrentName() == "NAME":
				iff.enterChunk("NAME")
				self.effect = iff.read_string()
				iff.exitChunk("NAME")
				
			iff.exitForm(version)
		else:			
			print(f"{iff.filename}: unsupported SSHT Version: {version}!")
		iff.exitForm("SSHT")

	def load_swts(self, iff):
		iff.enterForm("SWTS")
		version = iff.getCurrentName()
		if version in ["0000"]:			
			iff.enterForm(version)
			if iff.getCurrentName() == "NAME":
				iff.enterChunk("NAME")
				self.effect = iff.read_string()
				iff.exitChunk("NAME")

class SPS(object):
	__slots__ = ('no', 'shader', 'flags', 'verts', 'tris', 'full_shader_path', 'real_shader')
	def __init__(self):
		self.no = 0
		self.shader = ""
		self.flags = 0
		self.verts = []
		self.tris = []
		self.full_shader_path = None
		self.real_shader = None

	def __init__(self, no , shader, flags, verts, tris):
		self.no = no
		self.shader = shader
		self.flags = flags
		self.verts = verts
		self.tris = tris
		self.full_shader_path = None
		self.real_shader = None

	def hasDOT3(self):
		num_uv_sets = vertex_buffer_format.getNumberOfTextureCoordinateSets(self.flags)
		if(num_uv_sets > 0):
			return (vertex_buffer_format.getTextureCoordinateSetDimension(self.flags, num_uv_sets - 1) == 4)
		return False

	def hasColor0(self):
		return vertex_buffer_format.hasColor0(self.flags)

	def hasColor1(self):
		return vertex_buffer_format.hasColor1(self.flags)

	def getNumUVSets(self):
		num_uv_sets = vertex_buffer_format.getNumberOfTextureCoordinateSets(self.flags)
		if(num_uv_sets > 0):
			if(vertex_buffer_format.getTextureCoordinateSetDimension(self.flags, num_uv_sets - 1) == 4):
				num_uv_sets -= 1
		return num_uv_sets

	def stripped_shader_name(self):
		if self.shader == "":
			return "defaultappearance"
		else:
			return self.shader.split('/')[1].split('.')[0]

	def __str__(self):
		return f"SPS_No: {self.no} Shader: {self.shader} Flags: {self.flags} Verts: {len(self.verts)} Tris: {len(self.tris)}"

	def __repr__(self):
		return self.__str__()

class SWGMesh(object):
	__slots__ = ('filename', 'spss', 'extents', 'collision', 'realCollision', 'hardpoints', 'floor', 'root_dir')
	def __init__(self, filename, root):
		global SWG_ROOT
		SWG_ROOT = root
		self.filename = filename
		self.spss = []
		self.extents = []
		self.collision = None
		self.realCollision = None
		self.hardpoints = []
		self.floor = ""
		#self.root_dir = root

	def __str__(self):
		s = f"Filename: {self.filename}\nExtents: {str(self.extents)}\nCollision: {str(self.collision_summary_str())}\nSPS: {len(self.spss)}\n"
		for sps in self.spss:
			s += str(sps)+'\n'
		return s
		
	def __repr__(self):
		return self.__str__()

	def collision_summary_str(self):
		if self.collision:
			first = self.collision[8:12].decode('ASCII')
			return f'Type: {first} Len: {len(self.collision)}'
		else: 
			return "(No Collision)"

	def debug_flags(self, flags, sps_no):

		num_uv_sets = vertex_buffer_format.getNumberOfTextureCoordinateSets(flags)
		print(f'Mesh: {self.filename} SPS: {sps_no} Flags: {flags}')
		print(f'  hasPosition: {vertex_buffer_format.hasPosition(flags)}')
		print(f'  isTransformed: {vertex_buffer_format.isTransformed(flags)}')
		print(f'  hasNormal: {vertex_buffer_format.hasNormal(flags)}')
		print(f'  hasColor0: {vertex_buffer_format.hasColor0(flags)}')
		print(f'  hasColor1: {vertex_buffer_format.hasColor1(flags)}')
		print(f'  hasPointSize: {vertex_buffer_format.hasPointSize(flags)}')
		print(f'  uvSets: {vertex_buffer_format.getNumberOfTextureCoordinateSets(flags)}')
		for i in range(0, num_uv_sets):			
			print(f'  uvDim [{i}]: {vertex_buffer_format.getTextureCoordinateSetDimension(flags, i)}')

		if(num_uv_sets > 0) and (vertex_buffer_format.getTextureCoordinateSetDimension(flags, num_uv_sets - 1) == 4):		 
			print(f'Mesh: {self.filename} SPS: {sps_no} Flags: {flags}: Has DOT3!')

		if vertex_buffer_format.hasPointSize(flags):
			print(f'Mesh: {self.filename} SPS: {sps_no} Flags: {flags}: Has PointSize. Never seen that before! Not doing anything with it FYI')
		
		if vertex_buffer_format.hasColor1(flags):
			print(f'Mesh: {self.filename} SPS: {sps_no} Flags: {flags}: Has Color1. Never seen that before! Not doing anything with it FYI')


	def read_vertex(self, flags, iff):
		v = SWGVertex()

		num_uv_sets = vertex_buffer_format.getNumberOfTextureCoordinateSets(flags)
		skip_dot3 = False
		if(num_uv_sets > 0) and (vertex_buffer_format.getTextureCoordinateSetDimension(flags, num_uv_sets - 1) == 4):
			skip_dot3 = True
			num_uv_sets -= 1

		v.texs = []

		if vertex_buffer_format.hasPosition(flags):
			v.pos =  Vector(iff.read_vector3())

		if vertex_buffer_format.hasNormal(flags):
			v.normal =  Vector(iff.read_vector3())

		if vertex_buffer_format.hasPointSize(flags):
			point_size = iff.read_float() # unused

		if vertex_buffer_format.hasColor0(flags):
			# NSG Seems like this should be ARGB per SOE code, but that makes 
			# the Anchorhead Cantina look gross. Used trial and error to determine
			# order: BGRA
			b = iff.read_color()
			g = iff.read_color()
			r = iff.read_color()
			a = iff.read_color()
			v.color0 = [r,g,b,a]

		if vertex_buffer_format.hasColor1(flags):
			# NSG Seems like this should be ARGB per SOE code, but that makes 
			# the Anchorhead Cantina look gross. Used trial and error to determine
			# order: BGRA
			b = iff.read_color()
			g = iff.read_color()
			r = iff.read_color()
			a = iff.read_color()
			v.color1 = [r,g,b,a]

		for i in range(0, num_uv_sets):
			dim = vertex_buffer_format.getTextureCoordinateSetDimension(flags, i)
			v.texs.append([]) 
			for j in range(0, dim):
				v.texs[i].append(iff.read_float())

		if skip_dot3:
			iff.read_float()
			iff.read_float()
			iff.read_float()
			iff.read_float()

		return v

	def update_vertex(self, flags, iff, dx, dy, dz):
		v = SWGVertex()

		num_uv_sets = vertex_buffer_format.getNumberOfTextureCoordinateSets(flags)
		skip_dot3 = False
		if(num_uv_sets > 0) and (vertex_buffer_format.getTextureCoordinateSetDimension(flags, num_uv_sets - 1) == 4):
			skip_dot3 = True
			num_uv_sets -= 1

		v.texs = []

		if vertex_buffer_format.hasPosition(flags):
			x = iff.update_float(dx)
			y = iff.update_float(dy)
			z = iff.update_float(dz)
			v.pos=Vector([x,y,z])

		if vertex_buffer_format.hasNormal(flags):
			v.normal =  Vector(iff.read_vector3())

		if vertex_buffer_format.hasPointSize(flags):
			point_size = iff.read_float() # unused

		if vertex_buffer_format.hasColor0(flags):
			# NSG Seems like this should be ARGB per SOE code, but that makes 
			# the Anchorhead Cantina look gross. Used trial and error to determine
			# order: BGRA
			b = iff.read_color()
			g = iff.read_color()
			r = iff.read_color()
			a = iff.read_color()
			v.color0 = [r,g,b,a]

		if vertex_buffer_format.hasColor1(flags):
			# NSG Seems like this should be ARGB per SOE code, but that makes 
			# the Anchorhead Cantina look gross. Used trial and error to determine
			# order: BGRA
			b = iff.read_color()
			g = iff.read_color()
			r = iff.read_color()
			a = iff.read_color()
			v.color1 = [r,g,b,a]

		for i in range(0, num_uv_sets):
			dim = vertex_buffer_format.getTextureCoordinateSetDimension(flags, i)
			v.texs.append([]) 
			for j in range(0, dim):
				v.texs[i].append(iff.read_float())

		if skip_dot3:
			iff.read_float()
			iff.read_float()
			iff.read_float()
			iff.read_float()

		return v

	def load(self):
		iff = nsg_iff.IFF(filename=self.filename)
		#print(f"Name: {iff.getCurrentName()} Length: {iff.getCurrentLength()}")
		iff.enterAnyForm()
		version = iff.getCurrentName()

		if version not in ["0005", "0004"]:
			print(f'Unsupported MESH version: {version}')
			return False

		iff.enterForm(version)
		#print(iff.getCurrentName())
		iff.enterForm("APPR")

		appr_version = iff.getCurrentName()

		if appr_version == "0003":
			iff.enterAnyForm()			

			self.extents = extents.Extents.create(iff)

			self.collision = extents.Extents.create(iff)

			#hardpoints
			iff.enterForm("HPTS", True, False)
			while not iff.atEndOfForm():
				iff.enterChunk("HPNT", True)
				rotXx = iff.read_float()
				rotXy = iff.read_float()
				rotXz = iff.read_float()
				posX = iff.read_float()
				rotYx = iff.read_float()
				rotYy = iff.read_float()
				rotYz = iff.read_float()
				posY = iff.read_float()
				rotZx = iff.read_float()
				rotZy = iff.read_float()
				rotZz = iff.read_float()
				posZ = iff.read_float()
				hpntName = iff.read_string()
				self.hardpoints.append([rotXx, rotXy, rotXz, -posX, rotYx, rotYy, rotYz, posY, rotZx, rotZy, rotZz, posZ, hpntName])
				iff.exitChunk("HPNT")
			iff.exitForm("HPTS")

			if iff.enterForm("FLOR", True):
				if iff.enterChunk("DATA", True):
					self.floor = iff.read_string()
					iff.exitChunk("DATA")
				iff.exitForm("FLOR")
			
			iff.exitForm()
		else:
			print(f"Warning: Unknown APPR version: {appr_version}")

		iff.exitForm("APPR")

		iff.enterForm("SPS ")
		iff.enterForm("0001")
		iff.enterChunk("CNT ")
		cnt = iff.read_uint32()
		iff.exitChunk("CNT ")

		while(not iff.atEndOfForm()):
			sps_no = iff.getCurrentName()
			iff.enterAnyForm()

			iff.enterChunk("NAME")
			sht=iff.read_string()
			iff.exitChunk("NAME")
			#print(f"SPS {sps_no} Shader: {sht}")

			#print(f"Next: {iff.getCurrentName()}")
			iff.enterChunk("INFO")
			cnt=iff.read_uint32()
			iff.exitChunk("INFO")

			version=iff.getCurrentName()
			if version in ["0000", "0001"]:
				iff.enterForm(version)
				iff.enterChunk("INFO")
				iff.exitChunk("INFO")

				iff.enterForm("VTXA")
				iff.enterForm("0003")

				iff.enterChunk("INFO")
				bit_flag = iff.read_int32()
				#self.debug_flags(bit_flag, sps_no)
				num_verts = iff.read_uint32()
				verts = [None] * num_verts
				iff.exitChunk("INFO")

				iff.enterChunk("DATA")
				for i in range(0, num_verts):
					verts[i] = self.read_vertex(bit_flag, iff)

				iff.exitChunk("DATA")
				iff.exitForm("0003")

				iff.exitForm("VTXA")

				size = iff.getCurrentLength()
				iff.enterChunk("INDX")
				indexes = []
				index_count = iff.read_uint32()
				bpi = (size - 4) // index_count
				#print(f'Size: {size} Size - 4: {size - 4}, index_count: {index_count} bpi: {bpi}')
				for i in range(index_count//3):
					tri = Triangle()
					if(bpi == 2):
						tri.p1 = iff.read_int16()
						tri.p2 = iff.read_int16()
						tri.p3 = iff.read_int16()
					elif(bpi == 4):
						tri.p1 = iff.read_int32()
						tri.p2 = iff.read_int32()
						tri.p3 = iff.read_int32()
					indexes.append(tri)
				#print(f'Read Index Count: {index_count}')

				iff.exitChunk("INDX")
				iff.exitForm(version)
				print(f"SPS {sps_no} Shader: {sht} Version: {version} Verts: {len(verts)} Tris: {len(indexes)}")

				sps = SPS(sps_no, sht, bit_flag, verts, indexes)

				real_shader_path = support.find_file(sps.shader, SWG_ROOT)
				if real_shader_path:
					sps.full_shader_path = real_shader_path
					sps.real_shader = SWGShader(sps.full_shader_path, SWG_ROOT)
				else:
					print(f"Couldn't locate real shader path for: {sps.shader}")
				self.spss.append(sps)

			else:
				print(f"Warning: Unknown SPS {sps_no} Unhandled version: {version}")
				
			iff.exitForm()

		return True
			
	def write(self, filename):
		iff = nsg_iff.IFF(initial_size=512000)
		# - BEGIN MESH		
		iff.insertForm("MESH")
		iff.insertForm("0005")

		# -- BEGIN APPR
		iff.insertForm("APPR")
		iff.insertForm("0003")

		self.extents.write(iff)

		extents.Extents.write(self.collision, iff)

		# --- BEGIN HARDPOINTS
		iff.insertForm("HPTS")
		if len(self.hardpoints) > 0:
			for hpnt in self.hardpoints:
				iff.insertChunk("HPNT")
				iff.insertFloat(hpnt[0])
				iff.insertFloat(hpnt[1])
				iff.insertFloat(hpnt[2])
				iff.insertFloat(hpnt[3]) #x pos
				iff.insertFloat(hpnt[4])
				iff.insertFloat(hpnt[5])
				iff.insertFloat(hpnt[6])
				iff.insertFloat(hpnt[7]) #y pos
				iff.insertFloat(hpnt[8])
				iff.insertFloat(hpnt[9])
				iff.insertFloat(hpnt[10])
				iff.insertFloat(hpnt[11]) #z pos
				iff.insertChunkString(hpnt[12]) #hpnt name
				iff.exitChunk("HPNT")
		iff.exitForm()
		# --- END HARDPOINTS

		# --- BEGIN FLOOR
		iff.insertForm("FLOR")
		iff.insertChunk("DATA")
		iff.insert_bool(False)
		iff.exitChunk("DATA")
		iff.exitForm("FLOR")
		# --- END EXTENTS

		# -- END APPR
		iff.exitForm("0003")
		iff.exitForm("APPR")

		# -- BEGIN SPS
		iff.insertForm("SPS ")
		iff.insertForm("0001")

		# --- BEGIN CNT
		iff.insertChunk("CNT ")
		iff.insert_uint32(len(self.spss))
		iff.exitChunk("CNT ")

		for i in range(0, len(self.spss)):
			sps = self.spss[i]
			#print(f'Adding SPS {str(i+1).zfill(4)}')
			iff.insertNumberedForm(i+1)
			iff.insertChunk("NAME")
			iff.insertChunkString(sps.shader)
			iff.exitChunk("NAME")
			iff.insertChunk("INFO")
			iff.insert_uint32(1) #"Shader primitive count" - Never seen anything other than 1
			iff.exitChunk("INFO")

			iff.insertForm("0001")
			iff.insertChunk("INFO")
			iff.insert_uint32(9)
			iff.insert_bool(True)
			iff.insert_bool(False)
			iff.exitChunk("INFO")
			iff.insertForm("VTXA")
			iff.insertForm("0003")
			iff.insertChunk("INFO")
			#iff.insert_uint32(4357)
			#iff.insert_uint32(53765)
			iff.insert_uint32(sps.flags)
			self.debug_flags(sps.flags, i)
			iff.insert_uint32(len(sps.verts))
			iff.exitChunk("INFO")
			iff.insertChunk("DATA")
			for v in sps.verts:
				iff.insertFloatVector3((v.pos.x, v.pos.y, v.pos.z))

				if vertex_buffer_format.isTransformed(sps.flags):
					iff.insertFloat(1)
				
				iff.insertFloatVector3((v.normal.x, v.normal.y, v.normal.z))
				
				if vertex_buffer_format.hasPointSize(sps.flags):
					iff.insertFloat(1)

				if vertex_buffer_format.hasColor0(sps.flags):
					iff.insert_color(v.color0)

				if vertex_buffer_format.hasColor1(sps.flags):
					iff.insert_color(v.color1)
				
				for uv_set in v.texs:
					for value in uv_set:
						iff.insertFloat(value)
			iff.exitChunk("DATA")
			iff.exitForm("0003")
			iff.exitForm("VTXA")

			iff.insertChunk("INDX")
			iff.insert_uint32(len(sps.tris)*3)
			for t in sps.tris:
				iff.insert_uint16(t.p1)
				iff.insert_uint16(t.p2)
				iff.insert_uint16(t.p3)
			iff.exitChunk("INDX")

			iff.exitForm("0001")
			iff.exitForm()


		# -- END APPR
		iff.exitForm("0001")
		iff.exitForm("SPS ")

		iff.write(filename)	
		
class SWGBLendShape(object):
	def __init__(self):
		self.name = ""
		self.positions = []
		self.normals = []
		self.dot3 = None

	def __str__(self):
		return f"""Name: {self.name} Positions: {str(len(self.positions))} Norms: {str(len(self.normals))} DOT3: {(str(len(self.dot3)) if self.dot3 else "N/A")}"""

	def __repr__(self):
		return self.__str__()

class SWGPerShaderData(object):
	def __init__(self):
		self.name = ""
		self.pidx = []
		self.nidx = []
		self.dot3 = None
		self.colors = None
		self.txci = []
		self.tcsd = []
		self.num_uvs = 0
		self.uv_dimensions = []
		self.uvs = []
		self.num_prims = 0
		self.prims = []
		self.full_shader_path = None
		self.real_shader = None

	def __str__(self):
		s = f"""Name: {self.name} pidx: {str(len(self.pidx))} nidx: {str(len(self.nidx))} DOT3: {(str(len(self.dot3)) if self.dot3 else "N/A")}"""
		s += "\n"
		s += f"""UVS: {self.num_uvs} -- {', '.join( ("UVs: " + str(len(x)) + " Dim: " + str(len(x[0]))) for x in self.uvs)}"""
		s += "\n"
		s += f"""Prims: {self.num_prims} -- {', '.join( ("Tris: " + str(len(x))) for x in self.prims)}"""
		return s

	def __repr__(self):
		return self.__str__()

	def stripped_shader_name(self):
		if self.name == "":
			return "defaultappearance"
		else:
			return self.name.split('/')[1].split('.')[0]

class SWGMgn(object):
	def __init__(self, filename, root):
		global SWG_ROOT
		SWG_ROOT = root

		self.filename = filename

		self.max_transforms_vertex = 0
		self.max_transforms_shader = 0

		self.num_skeletons = 0
		self.num_vertex_groups = 0
		self.num_positions = 0
		self.num_transform_weight_data = 0
		self.num_normals = 0
		self.num_shaders = 0
		self.num_blends = 0
		
		self.num_occ_zones = 0
		self.num_occ_combo_zones = 0
		self.num_this_occludes = 0
		self.occlusion_layer = 2

		self.occlusions = []
		self.occlusion_zones = None
		self.skeletons = []
		self.joint_names = []

		self.positions = []
		self.normals = []
		self.dot3 = None

		self.twhd = []
		self.twdt = []

		self.vertex_weights = []

		self.blends = []

		self.psdts = []

		self.dynamic_hardpoints = None
		self.static_hardpoints = None

		self.binary_hardpoints = None
		self.binary_trts = None

	def __str__(self):
		s = f"""Filename: {self.filename} 
				max_transforms_vertex: {self.max_transforms_vertex}, 
				max_transforms_shader: {self.max_transforms_shader},
				self.num_skeletons {self.num_skeletons},
				self.num_vertex_groups: {self.num_vertex_groups},
				self.num_positions: {self.num_positions},
				self.num_transform_weight_data: {self.num_transform_weight_data},
				self.num_normals: {self.num_normals},
				self.num_shaders: {self.num_shaders},
				self.num_blends: {self.num_blends},
				self.num_occ_zones: {self.num_occ_zones},
				self.num_occ_combo_zones: {self.num_occ_combo_zones},
				self.num_this_occludes: {len(self.occlusions)},
				self.occlusion_layer: {self.occlusion_layer}
				self.skeletons: {",".join(self.skeletons)}
				self.joint_names: {",".join(self.joint_names)}
				self.positions: {len(self.positions)}
				self.twhd: {len(self.twhd)}
				self.twdt: {len(self.twdt)}
				self.dot3: {(str(len(self.dot3)) if self.dot3 else "NA")}
				self.occlusions: {', '.join(str(x) for x in self.occlusions)}
				self.occlusion_zones: {((', '.join(str(x) for x in self.occlusion_zones)) if self.occlusion_zones else "NONE")}
				self.dynamic_hardpoints: {((', '.join(str(x) for x in self.dynamic_hardpoints)) if self.dynamic_hardpoints else "NONE")}
				self.static_hardpoints: {((', '.join(str(x) for x in self.static_hardpoints)) if self.static_hardpoints else "NONE")}
				"""
		#s += "\n".join(str(x) for x in self.positions)
		s += 'Blends: \n' + "\n".join(str(x) for x in self.blends)

		s += 'Per Shader Data: \n' + "\n".join(str(x) for x in self.psdts)
		return s
		
	def __repr__(self):
		return self.__str__()

	def normalize_vertex_weights(self, weights):
		for i , posn in enumerate(weights):
			total = 0
			for weight in posn:
				total += weight[1]

			for weight in posn:
				before = weight[1]
				weight[1] = weight[1]/total 
				if weight[1] != before:
					print(f"Vert {i} changed weight for bone {weight[0]} from {before} to {weight[1]}")

	def compute_fully_occluded_zone_combination(self):
		result=set()
		if self.occlusion_zones and len(self.occlusion_zones) > 0:
			for occ in self.occlusion_zones:
				if len(occ[1]) == 0:
					continue
				else:
					for name in occ[0].split(":"):
						for ozn in self.occlusions:
							if ozn[0] == name:
								result.add(ozn[1])
		return result

		
	def load(self):
		iff = nsg_iff.IFF(filename=self.filename)
		print(f"Name: {iff.getCurrentName()} Length: {iff.getCurrentLength()}")
		iff.enterAnyForm()
		version = iff.getCurrentName()

		if version not in ["0003", "0004",]:
			print(f'Unsupported MGN version: {version}')
			return False
		
		print(f'Doing Mgn version: {version}')

		iff.enterForm(version)
		#print(iff.getCurrentName())
		iff.enterChunk("INFO")

		self.max_transforms_vertex = iff.read_int32()
		self.max_transforms_shader = iff.read_int32()

		self.num_skeletons = iff.read_int32()
		self.num_vertex_groups = iff.read_int32()
		self.num_positions = iff.read_int32()
		self.num_transform_weight_data = iff.read_int32()
		self.num_normals = iff.read_int32()
		self.num_shaders = iff.read_int32()
		self.num_blends = iff.read_int32()
		
		self.num_occ_zones = iff.read_int16()
		self.num_occ_combo_zones = iff.read_int16()
		self.num_this_occludes = iff.read_int16()
		self.occlusion_layer = iff.read_int16() 

		iff.exitChunk("INFO")
		
		iff.enterChunk("SKTM")
		while not iff.atEndOfForm():
			self.skeletons.append(iff.read_string())
		iff.exitChunk("SKTM")
		
		iff.enterChunk("XFNM")
		while not iff.atEndOfForm():
			self.joint_names.append(iff.read_string())
		iff.exitChunk("XFNM")

		iff.enterChunk("POSN")  
		self.positions = [0] * self.num_positions
		i=0	  
		while not iff.atEndOfForm():
			self.positions[i] = (iff.read_float(), iff.read_float(), -iff.read_float())
			i += 1
		iff.exitChunk("POSN")

		self.twhd = [0] * self.num_positions
		i = 0
		iff.enterChunk("TWHD")		
		while not iff.atEndOfForm():
			self.twhd[i] = iff.read_uint32()
			i += 1
		iff.exitChunk("TWHD")

		iff.enterChunk("TWDT")	 
		self.twdt = [[0,0.0]] * self.num_transform_weight_data   
		i = 0
		while not iff.atEndOfForm():
			self.twdt[i] = [iff.read_uint32(), iff.read_float()]
			#print(f'Twdt: {i} ({str(self.twdt[i])})')
			#print(f"TWDT[{i}] {self.twdt[i][0]} = {self.twdt[i][1]}")
			i += 1
		iff.exitChunk("TWDT")

		j = 0
		i = 0
		p = 0
		self.vertex_weights = [None] * self.num_positions
		for p, h in enumerate(self.twhd):
			these_weights = []
			sum=0
			for x in range(0,h):
				twdt = self.twdt[i]
				sum += twdt[1]
				these_weights.append(twdt)
				i += 1
			
			# if sum != 1.0:
			#	 print(f' *** WARN ***: Vertex Weight sum for vert: {p} != 1.0 : {sum}')
			self.vertex_weights[p] = these_weights
			
			# sorted_weights = sorted(these_weights, key=lambda x: x[0])
			# for weight in sorted_weights:				
			#	 print(f"TWDT[{j}] {weight[0]} = {weight[1]}")
			#	 j+=1
		
		#self.normalize_vertex_weights(self.vertex_weights)

		#self.positions = list(zip(self.positions, self.vertex_weights))

		iff.enterChunk("NORM")	 
		self.normals = [None] * self.num_normals   
		i = 0
		while not iff.atEndOfForm():
			self.normals[i] = (iff.read_float(), iff.read_float(), iff.read_float())
			i += 1
		iff.exitChunk("NORM")

		if iff.getCurrentName() == "DOT3":
			iff.enterChunk("DOT3")	 
			num_dot3 = iff.read_uint32()
			self.dot3 = [None] * num_dot3   
			i = 0
			while not iff.atEndOfForm():
				self.dot3[i] = [iff.read_float(), iff.read_float(), iff.read_float(), iff.read_float()]
				i += 1
			iff.exitChunk("DOT3")

		if iff.getCurrentName() == "HPTS":
			data_length = iff.getCurrentLength() + 8
			form_name = iff.getCurrentName()
			self.binary_hardpoints = iff.read_misc(data_length)
			print(f"binary_hardpoints form: {data_length} Len: {form_name}")

			#iff.enterForm("HPTS")
			# if iff.getCurrentName() == "STAT":
			#	 iff.enterChunk("STAT")
			#	 self.static_hardpoints = []
			#	 count = iff.read_int16()
			#	 while not iff.atEndOfForm():
			#		 self.static_hardpoints.append(MgnHardpoint(iff.read_string(), iff.read_string(), iff.read_vector4(), iff.read_vector3()))
			#	 iff.exitChunk("STAT")
			# if iff.getCurrentName() == "DYN ":
			#	 iff.enterChunk("DYN ")
			#	 count = iff.read_int16()
			#	 self.dynamic_hardpoints = []
			#	 while not iff.atEndOfForm():
			#		 self.dynamic_hardpoints.append(MgnHardpoint(iff.read_string(), iff.read_string(), iff.read_vector4(), iff.read_vector3()))
			#	 iff.exitChunk("DYN ")  
			#iff.exitForm("HPTS")

		if iff.getCurrentName() == "BLTS":
			iff.enterForm("BLTS")
			while not iff.atEndOfForm():
				iff.enterForm("BLT ")
				blt = SWGBLendShape()
				iff.enterChunk("INFO")
				num_positions = iff.read_uint32()
				num_norms = iff.read_uint32()
				blt.name = iff.read_string()
				iff.exitChunk("INFO")
				self.blends.append(blt)

				if iff.getCurrentName() == "POSN":
					iff.enterChunk("POSN")
					while not iff.atEndOfForm():
						blt.positions.append( (iff.read_uint32(), (iff.read_float(), iff.read_float(), iff.read_float())))
					iff.exitChunk("POSN")

				if iff.getCurrentName == "NORM":
					iff.enterChunk("NORM")
					while not iff.atEndOfForm():
						blt.normals.append( (iff.read_uint32(), (iff.read_float(), iff.read_float(), iff.read_float())))
					iff.exitChunk("NORM")

				if iff.getCurrentName() == "DOT3":
					iff.enterChunk("DOT3")	 
					num_dot3 = iff.read_int32()
					blt.dot3 = []
					#for i in range(0, num_dot3):
					while not iff.atEndOfForm():
						blt.dot3.append([(iff.read_int32(), (iff.read_float(), iff.read_float(), iff.read_float()))])
					iff.exitChunk("DOT3")

				iff.exitForm("BLT ")
			iff.exitForm("BLTS")

		if iff.getCurrentName() == "OZN ":
			iff.enterChunk("OZN ")
			i = 0
			while not iff.atEndOfForm():
				self.occlusions.append([iff.read_string(), i, 0])
				i += 1
			iff.exitChunk("OZN ")

		# We don't really need to do anything with this.
		# FOZC (Fully Occluded Zone Combination) is the combination of occlusion zones which would fully
		# occlude this mesh, which helps the client quickly determine it doesn't need to render this mesh
		# if a higher mesh occludes all those zones, rather than doing it per-triangle. From a Blender
		# perspective, we need to compute this on export, but don't need it for import.

		if iff.getCurrentName() == "FOZC":
			iff.enterChunk("FOZC")
			iff.exitChunk("FOZC")

		if iff.getCurrentName() == "OZC ":
			iff.enterChunk("OZC ")
			self.occlusion_zones=[]
			while not iff.atEndOfForm():
				this_zone=[]
				count = iff.read_int16()
				for i in range(0,count):
					n = iff.read_int16()
					this_zone.append(next(x[0] for x in self.occlusions if x[1] == n))
				self.occlusion_zones.append([":".join(this_zone),[]])
			iff.exitChunk("OZC ")

		if iff.getCurrentName() == "ZTO ":
			iff.enterChunk("ZTO ")
			for occ in self.occlusions:
				occ[2] = 0
			while not iff.atEndOfForm():
				index = iff.read_int16()
				for occ in self.occlusions:
					if occ[1] == index:
						occ[2] = 1
						#print(f"Occ: {str(occ)} is ZTO: {index} Setting occluded to: {occ[2]}")
			iff.exitChunk("ZTO ")

		global_tri_index=0
		while iff.getCurrentName() == "PSDT":
			psdt = SWGPerShaderData()
			iff.enterForm("PSDT")

			iff.enterChunk("NAME")
			psdt.name = iff.read_string()
			real_shader_path = support.find_file(psdt.name, SWG_ROOT)
			if real_shader_path:
				psdt.full_shader_path = real_shader_path
				psdt.real_shader = SWGShader(psdt.full_shader_path, SWG_ROOT)
			else:
				print(f"Couldn't locate real shader path for: {psdt.name}")

			iff.exitChunk("NAME")

			iff.enterChunk("PIDX")
			num = iff.read_uint32()
			while not iff.atEndOfForm():
				i = iff.read_uint32()
				psdt.pidx.append(i)

			iff.exitChunk("PIDX")

			iff.enterChunk("NIDX")
			while not iff.atEndOfForm():
				psdt.nidx.append(iff.read_uint32())
			iff.exitChunk("NIDX")

			if iff.getCurrentName() == "DOT3":
				psdt.dot3 = []
				iff.enterChunk("DOT3")
				while not iff.atEndOfForm():
					psdt.dot3.append(iff.read_uint32())
				iff.exitChunk("DOT3")

			if iff.getCurrentName() == "VDCL":
				psdt.colors = []
				iff.enterChunk("VDCL")
				while not iff.atEndOfForm():
					psdt.colors.append([iff.read_byte(), iff.read_byte(), iff.read_byte(), iff.read_byte()])
				iff.exitChunk("VDCL")

			if iff.getCurrentName() == "TXCI":
				iff.enterChunk("TXCI")
				psdt.num_uvs = iff.read_uint32()
				while not iff.atEndOfForm():
					psdt.uv_dimensions.append(iff.read_uint32())
				iff.exitChunk("TXCI")

				iff.enterForm("TCSF")
				i = 0
				while not iff.atEndOfForm(): 
					dim = psdt.uv_dimensions[i]
					num = iff.getCurrentLength() // 4 // dim			 
					psdt.uvs.append([None] * num)				 
					iff.enterChunk("TCSD")
					for n in range(0, num):
						uv = []
						for m in range(0, dim):
							uv.append(iff.read_float())
						psdt.uvs[i][n] = uv
					iff.exitChunk("TCSD")					
					i += 1
				iff.exitForm("TCSF")

			iff.enterForm("PRIM")
			iff.enterChunk("INFO")
			psdt.num_prims = iff.read_uint32()
			iff.exitChunk("INFO")
			while not iff.atEndOfForm():
				prim_type = iff.getCurrentName()
				iff.enterChunk(prim_type)

				triangle_list = []
				if prim_type == "OITL":
					num_tris = iff.read_uint32()
					#for n in range(0, num_tris):
					while not iff.atEndOfForm():
						occ = iff.read_int16()
						self.occlusion_zones[occ][1].append(global_tri_index)
						global_tri_index += 1
						p1 = iff.read_int32()
						p2 = iff.read_int32()
						p3 = iff.read_int32()
						tri = Triangle(p1, p2, p3)
						triangle_list.append(tri)
					psdt.prims.append(triangle_list)
				elif prim_type == "ITL ":
					num_tris = iff.read_uint32()
					for n in range(0, num_tris):
						p1 = iff.read_int32()
						p2 = iff.read_int32()
						p3 = iff.read_int32()
						tri = Triangle(p1, p2, p3)
						triangle_list.append(tri)
					psdt.prims.append(triangle_list)
				else:
					print(f'Unhandled PRIM type: {prim_type}')
				iff.exitChunk(prim_type)

			iff.exitForm("PRIM")
			self.psdts.append(psdt)
			iff.exitForm("PSDT")

		if iff.getCurrentName() == "TRTS":
			data_length = iff.getCurrentLength() + 8
			form_name = iff.getCurrentName()
			self.binary_trts = iff.read_misc(data_length)
			print(f"binary_trts form: {data_length} Len: {form_name}")


		print(self)

	def get_zones_this_occludes(self):
		i = 0
		for zone in self.occlusions:
			if zone[2] == 1:
				i += 1
		return i

	def write(self):
		tris_with_no_facemap=[]
		iff = nsg_iff.IFF(initial_size=512000)
		print(f"Name: {iff.getCurrentName()} Length: {iff.getCurrentLength()}")
		iff.insertForm("SKMG")
		iff.insertForm("0004")

		iff.insertChunk("INFO")
		iff.insert_int32(self.max_transforms_vertex)
		iff.insert_int32(self.max_transforms_shader)
		iff.insert_int32(len(self.skeletons))
		iff.insert_int32(len(self.joint_names))
		iff.insert_int32(len(self.positions))
		iff.insert_int32(len([vv for v in self.twdt for vv in v ]))
		iff.insert_int32(len(self.normals))
		iff.insert_int32(len(self.psdts))
		iff.insert_int32(len(self.blends))
		
		iff.insert_int16(len(self.occlusions))
		iff.insert_int16(len(self.occlusion_zones) if self.occlusion_zones else 0)
		iff.insert_int16(self.get_zones_this_occludes())
		iff.insert_int16(self.occlusion_layer) 
		iff.exitChunk("INFO")
		
		iff.insertChunk("SKTM")
		for skel in self.skeletons:
			iff.insertChunkString(skel)
		iff.exitChunk("SKTM")

		iff.insertChunk("XFNM")
		for bone in self.joint_names:
			iff.insertChunkString(bone)
		iff.exitChunk("XFNM")

		iff.insertChunk("POSN")
		for pos in self.positions:
			#pos[0] = -pos[0]
			iff.insertFloatVector3(pos)
		iff.exitChunk("POSN")

		iff.insertChunk("TWHD")
		for twdt in self.twdt:
			iff.insert_uint32(len(twdt))
		iff.exitChunk("TWHD")
		
		iff.insertChunk("TWDT")
		i = 0
		for twdt in self.twdt:
			sorted_weights=sorted(twdt, key=lambda x: x[1], reverse=True)
			for weight in sorted_weights:
				iff.insert_uint32(weight[0])
				iff.insertFloat(weight[1])
				#print(f"TWDT[{i}] {weight[0]} = {weight[1]}")
				i += 1
		iff.exitChunk("TWDT")

		iff.insertChunk("NORM")
		for norm in self.normals:
			iff.insertFloatVector3(norm)
		iff.exitChunk("NORM") 

		if self.dot3:
			iff.insertChunk("DOT3")
			iff.insert_uint32(len(self.dot3))
			for dot3 in self.dot3:
				iff.insertFloatVector4(dot3)
			iff.exitChunk("DOT3")
		
		if self.binary_hardpoints:
			iff.insertForm(self.binary_hardpoints[8:12].decode('ASCII'))
			iff.insertIffData(self.binary_hardpoints[12:])
			iff.exitForm()
		
		if(len(self.blends) > 0):
			iff.insertForm("BLTS")
			for blend in self.blends:
				iff.insertForm("BLT ")

				iff.insertChunk("INFO")
				iff.insert_uint32(len(blend.positions))
				iff.insert_uint32(len(blend.normals))
				iff.insertChunkString(blend.name)
				iff.exitChunk("INFO")

				iff.insertChunk("POSN")
				for p in blend.positions:
					iff.insert_uint32(p[0])
					iff.insertFloatVector3(p[1])
				iff.exitChunk("POSN")

				iff.insertChunk("NORM")
				for n in blend.normals:
					iff.insert_uint32(n[0])
					iff.insertFloatVector3(n[1])
				iff.exitChunk("NORM")

				if blend.dot3:
					iff.insertChunk("DOT3")
					iff.insert_uint32(len(blend.dot3))
					for n in blend.dot3:
						iff.insert_uint32(n[0])
						iff.insertFloatVector3(n[1])
					iff.exitChunk("DOT3")

				iff.exitForm("BLT ")
			iff.exitForm("BLTS")

		if len(self.occlusions) > 0:
			iff.insertChunk("OZN ")
			for occ in self.occlusions:
				iff.insertChunkString(occ[0])
			iff.exitChunk("OZN ")

		fully_occluded_zone_combination=self.compute_fully_occluded_zone_combination()
		if len(fully_occluded_zone_combination) > 0:
			iff.insertChunk("FOZC")
			count=len(fully_occluded_zone_combination)
			iff.insert_int16(count)
			for zone in fully_occluded_zone_combination:
				iff.insert_int16(zone)
			iff.exitChunk("FOZC")

		if self.occlusion_zones and len(self.occlusion_zones) > 0:
			iff.insertChunk("OZC ")
			for i, occ in enumerate(self.occlusion_zones):
				print(f"OZC {i}: {occ[0]} has tris: {str(len(occ[1]))}")
				zones=occ[0].split(':')				
				iff.insert_int16(len(zones))
				for zone_name in zones:
					for zone in self.occlusions:
						if zone[0] == zone_name:
							iff.insert_int16(zone[1])
							print(f"Adding OZC {zone[1]} which is {zone_name}")
			iff.exitChunk("OZC ")

		occluded = [x for x in self.occlusions if x[2] == 1]			
		if len(occluded) > 0:
			iff.insertChunk("ZTO ")
			for occ in occluded:
					iff.insert_int16(occ[1])
			iff.exitChunk("ZTO ")

		global_tri_index=0
		for psdt in self.psdts:
			iff.insertForm("PSDT")
			iff.insertChunk("NAME")
			iff.insertChunkString(f'shader/{psdt.name}.sht')
			iff.exitChunk("NAME")

			iff.insertChunk("PIDX")
			iff.insert_uint32(len(psdt.pidx))
			for pidx in psdt.pidx:
				iff.insert_uint32(pidx)
			iff.exitChunk("PIDX")

			iff.insertChunk("NIDX")
			for nidx in psdt.nidx:
				iff.insert_uint32(nidx)
			iff.exitChunk("NIDX")

			if psdt.dot3:
				iff.insertChunk("DOT3")
				for dot3 in psdt.dot3:
					iff.insert_uint32(dot3)
				iff.exitChunk("DOT3")

			if len(psdt.uvs) > 0:
				iff.insertChunk("TXCI")
				iff.insert_int32(len(psdt.uvs))
				for uv_set in psdt.uvs:
					iff.insert_int32(len(uv_set[0]))
				iff.exitChunk("TXCI")

				iff.insertForm("TCSF")
				for uv_set in psdt.uvs:
					iff.insertChunk("TCSD")
					for uv in uv_set:
						iff.insertFloat(uv[0])
						iff.insertFloat(1 - uv[1]) 
					iff.exitChunk("TCSD")
				iff.exitForm("TCSF")

			iff.insertForm("PRIM")
			
			iff.insertChunk("INFO")
			iff.insert_uint32(len(psdt.prims))
			iff.exitChunk("INFO")

			if self.occlusion_zones:
				for prim in psdt.prims:
					iff.insertChunk("OITL")
					iff.insert_uint32(len(prim) // 3)
					for value in prim:
						if global_tri_index % 3 == 0:
							found=False
							for i, occ in enumerate(self.occlusion_zones):
								if (global_tri_index // 3) in occ[1]:
									iff.insert_int16(i)
									found=True
									break
							if not found:
								#print(f"WARNING: Tri: {global_tri_index // 3} Not in any Face Map (occlusion zone). Assuming 0!")
								tris_with_no_facemap.append(global_tri_index)
								iff.insert_int16(0)
						iff.insert_uint32(value)
						global_tri_index += 1
					iff.exitChunk("OITL")
			else:
				for prim in psdt.prims:
					iff.insertChunk("ITL ")
					iff.insert_uint32(len(prim) // 3)
					for value in prim:
						iff.insert_uint32(value)
					iff.exitChunk("ITL ")
			iff.exitForm("PRIM")
			
			iff.exitForm("PSDT")

		if self.binary_trts:
			iff.insertForm(self.binary_trts[8:12].decode('ASCII'))
			iff.insertIffData(self.binary_trts[12:])
			iff.exitForm()

		if self.occlusion_zones and len(tris_with_no_facemap) > 0:
			print(f"WARNING: Tris without assigned occlusion zone: {str(len(tris_with_no_facemap))}")
		iff.write(self.filename)
