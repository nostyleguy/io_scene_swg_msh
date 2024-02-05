from . import nsg_iff
from . import vector3D
from . import swg_types
from mathutils import Vector

class Extents():
    def __init__(self):
        pass

    def create(iff):
        tag = iff.getCurrentName()

        if tag == "NULL":
            iff.enterAnyForm()
            iff.exitForm()
            return None
        elif tag == "EXSP":
            return SphereExtents.create(iff)
        elif tag == "EXBX":
            return BoxExtents.create(iff)
        elif tag == "CMPT":
            return ComponentExtent.create(iff)
        elif tag == "CPST":
            return CompositeExtent.create(iff)
        elif tag == "CMSH":
            return MeshExtent.create(iff)
        elif tag == "DTAL":
            return DetailExtent.create(iff)
        elif tag == "XCYL":
            return CylinderExtent.create(iff)
        else:
            print(f"Unhandled extent type: {tag}")

        return None

    def write(extent, iff):
        if extent == None:
            extent = NullExtents()
        extent.write(iff)
            
class NullExtents(Extents):
    def __init__(self):
        pass

    def write(self, iff):        
        iff.insertForm("NULL")
        iff.exitForm("NULL")

class BoxExtents(Extents):
    def __init__(self):
        self.min = [0, 0, 0]
        self.max = [0, 0, 0]

    def __init__(self, min, max):
        self.min = min
        self.max = max

    def create(iff):

        iff.enterForm("EXBX")
        iff.enterForm("0001")

        iff.enterForm("EXSP")
        iff.exitForm("EXSP")

        iff.enterChunk("BOX ")
        min = vector3D.Vector3D(iff.read_float(), iff.read_float(), iff.read_float())
        max = vector3D.Vector3D(iff.read_float(), iff.read_float(), iff.read_float())
        #print(f"Min: {min} Max: {max}")
        iff.exitChunk("BOX ")
        iff.exitForm("0001")
        iff.exitForm("EXBX")
        return BoxExtents(min, max)

    def write(self, iff):
        iff.insertForm("EXBX")
        iff.insertForm("0001")

        iff.insertForm("EXSP")
        iff.insertForm("0001")
        iff.insertChunk("SPHR")
        max = Vector(self.max)
        min = Vector(self.min)
        center = (max + min) / 2.0
        diff = (max - min) / 2.0
        rad = diff.magnitude
        iff.insertFloatVector3(center[:])
        iff.insertFloat(rad)
        iff.exitChunk("SPHR")
        iff.exitForm("0001")
        iff.exitForm("EXSP")

        iff.insertChunk("BOX ")
        iff.insertFloatVector3(self.max)
        iff.insertFloatVector3(self.min)
        iff.exitChunk("BOX ")

        iff.exitForm("0001")
        iff.exitForm("EXBX")

    def getCenter(self):
        mag = (self.max - self.min) 
        vec =  vector3D.Vector3D(mag.x/2, mag.y/2, mag.z/2) + self.min
        return [vec.x,vec.y,vec.z]

    def getSize(self):
        return [abs(self.max.x - self.min.x)/2, abs(self.max.y - self.min.y)/2, abs(self.max.z - self.min.z)/2]

    def fromCenterAndScale(self, center, scale): 
        self.min = center - scale
        self.max = center + scale
        print(f"Center {center} Scale: {scale} Min: {self.min} Max: {self.max}")  


    def expand(self, other):
        if not isinstance(other, BoxExtents):
            print(f"Warning! Cannot use BoxExtents.expand with other type: {type(other)}. Only BoxExtents are supported!")
            return

        if other.min[0] < self.min[0]:
            self.min[0] = other.min[0]
        if other.min[1] < self.min[1]:
            self.min[1] = other.min[1]
        if other.min[2] < self.min[2]:
            self.min[2] = other.min[2]

        if other.max[0] > self.max[0]:
            self.max[0] = other.max[0]
        if other.max[1] > self.max[1]:
            self.max[1] = other.max[1]
        if other.max[2] > self.max[2]:
            self.max[2] = other.max[2]

class SphereExtents(Extents):
    def __init__(self, center, radius):
        self.center = center
        self.radius = radius

    def create(iff):
        iff.enterForm("EXSP")
        iff.enterForm("0001")
        iff.enterChunk("SPHR")
        center = iff.read_vector3()
        radius = iff.read_float()
        #print(f"Center: {center} Radius: {radius}")
        iff.exitChunk("SPHR")
        iff.exitForm("0001")
        iff.exitForm("EXSP")
        return SphereExtents(center, radius)

    def write(self, iff):
        iff.insertForm("EXSP")
        iff.insertForm("0001")
        iff.insertChunk("SPHR")
        iff.insertFloatVector3(self.center)
        iff.insertFloat(self.radius)
        iff.exitChunk("SPHR")
        iff.exitForm("0001")
        iff.exitForm("EXSP")


class CylinderExtent(Extents):
    def __init__(self, base, radius, height):
        self.base = base
        self.radius = radius
        self.height = height

    def create(iff):
        iff.enterForm("XCYL")
        iff.enterForm("0000")
        iff.enterChunk("CYLN")
        base = iff.read_vector3()
        radius = iff.read_float()
        height = iff.read_float()
        #print(f"Center: {center} Radius: {radius}")
        iff.exitChunk("CYLN")
        iff.exitForm("0000")
        iff.exitForm("XCYL")
        return CylinderExtent(base, radius, height)    

    def write(self, iff):
        iff.insertForm("XCYL")
        iff.insertForm("0000")
        iff.insertChunk("CYLN")
        iff.insertFloatVector3(self.base)
        iff.insertFloat(self.radius)
        iff.insertFloat(self.height)
        iff.exitChunk("CYLN")
        iff.exitForm("0000")
        iff.exitForm("XCYL")


class CompositeExtent (Extents):

    def create(iff):
        e = CompositeExtent()
        e.load(iff)
        return e

    def load(self, iff):
        iff.enterForm("CPST")
        iff.enterForm("0000")
        while (not iff.atEndOfForm()):
            self.extents.append(Extents.create(iff))
        iff.exitForm("0000")
        iff.exitForm("CPST")    

    def write(self, iff):
        iff.insertForm("CPST")
        iff.insertForm("0000")
        for e in self.extents:
            Extents.write(e, iff)
        iff.exitForm("0000")
        iff.exitForm("CPST")

    def __init__(self):
        self.extents = []

class ComponentExtent(Extents):

    def create(iff):
        e = ComponentExtent()
        e.load(iff)
        return e
    
    def __init__(self):
        self.extent = None

    def load(self, iff):
        iff.enterForm("CMPT")
        iff.enterForm("0000")
        self.extent = CompositeExtent.create(iff)
        iff.exitForm("0000")
        iff.exitForm("CMPT")

    def write(self, iff):
        iff.insertForm("CMPT")
        iff.insertForm("0000")
        Extents.write(self.extent, iff)
        iff.exitForm("0000")
        iff.exitForm("CMPT")

class DetailExtent(Extents):

    def create(iff):
        e = DetailExtent()
        e.load(iff)
        return e
    
    def __init__(self):
        self.broad_extent = None
        self.extents = None

    def load(self, iff):
        iff.enterForm("DTAL")
        iff.enterForm("0000")
        extents = CompositeExtent.create(iff).extents
        print(f"DTAL extent with {len(extents)}")
        if(len(extents) == 2):
            self.broad_extent = extents[0]
            self.extents = extents[1]
        else:
            print(f"Bad DetailExtent with child count: {len(extents)}")
        iff.exitForm("0000")
        iff.exitForm("DTAL")

    def write(self, iff):
        iff.insertForm("DTAL")
        iff.insertForm("0000")
        iff.insertForm("CPST")
        iff.insertForm("0000")
        Extents.write(self.broad_extent, iff)
        Extents.write(self.extents, iff)
        iff.exitForm("0000")
        iff.exitForm("CPST")
        iff.exitForm("0000")
        iff.exitForm("DTAL")


class MeshExtent(object):

    def create(iff):
        cmsh = MeshExtent()
        cmsh.load(iff)
        return cmsh
    
    def __init__(self):
        self.verts=[]
        self.triangles=[]

    def load(self, iff):
        iff.enterForm("CMSH")
        iff.enterForm("0000")
        idtl = swg_types.IndexedTriangleList()
        idtl.load(iff)
        self.verts = idtl.verts
        self.triangles = idtl.indexes
        iff.exitForm("0000")
        iff.exitForm("CMSH")

        print(f"Created CMSH with {len(self.verts)} verts and {len(self.triangles)} triangles!")

    def write(self, iff):        
        iff.insertForm("CMSH")
        iff.insertForm("0000")
        idtl = swg_types.IndexedTriangleList()
        idtl.verts = self.verts
        idtl.indexes = self.triangles
        idtl.write(iff)
        iff.exitForm("0000")
        iff.exitForm("CMSH")

