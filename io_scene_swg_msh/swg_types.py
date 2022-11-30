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

import math
from . import nsg_iff
from . import vector3D
from . import vertex_buffer_format

class SWGVertex(object):
    __slots = ('pos', 'normal', 'color', 'texs')
    def __init__(self):
        self.texs = []
        self.pos = None
        self.normal = None
        self.color = None

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

class SPS(object):
    __slots__ = ('no', 'shader', 'flags', 'verts', 'tris')
    def __init__(self):
        self.no = 0
        self.shader = ""
        self.flags = 0
        self.verts = []
        self.tris = []
    def __init__(self, no , shader, flags, verts, tris):
        self.no = no
        self.shader = shader
        self.flags = flags
        self.verts = verts
        self.tris = tris

    def __str__(self):
        return f"SPS_No: {self.no} Shader: {self.shader} Flags: {self.flags} Verts: {len(self.verts)} Tris: {len(self.tris)}"

    def __repr__(self):
        return self.__str__()

class SWGMesh(object):
    __slots__ = ('filename', 'spss', 'extents', 'collision', 'hardpoints', 'floor')
    def __init__(self, filename):
        self.filename = filename
        self.spss = []
        self.extents = []
        self.collision = None
        self.hardpoints = []
        self.floor = ""

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
        if(num_uv_sets > 0) and (vertex_buffer_format.getTextureCoordinateSetDimension(flags, num_uv_sets - 1) == 4):         
            print(f'Mesh: {self.filename} SPS: {sps_no} Flags: {flags}: Has deprecated DOT3 UVs. Will skip!')

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
            v.pos =  vector3D.Vector3D(iff.read_float(), iff.read_float(), iff.read_float())

        if vertex_buffer_format.hasNormal(flags):
            v.normal =  vector3D.Vector3D(iff.read_float(), iff.read_float(), iff.read_float())

        if vertex_buffer_format.hasPointSize(flags):
            point_size = iff.read_float() # unused

        if vertex_buffer_format.hasColor0(flags):
            v.color = iff.read_uint32()

        if vertex_buffer_format.hasColor1(flags):
            color1 = iff.read_uint32() # unused

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
            iff.enterForm("EXBX")
            iff.enterForm("0001")
            iff.enterForm("EXSP")
            iff.enterForm("0001")
            iff.enterChunk("SPHR")
            x = iff.read_float()
            y = iff.read_float()
            z = iff.read_float()
            rad = iff.read_float()
            #print(f"X: {x} Y: {y} Z: {z} Radius: {rad}")
            iff.exitChunk("SPHR")
            iff.exitForm("0001")
            iff.exitForm("EXSP")

            iff.enterChunk("BOX ")    
            maxx = iff.read_float()
            maxy = iff.read_float()
            maxz = iff.read_float()
            minx = iff.read_float()
            miny = iff.read_float()
            minz = iff.read_float()
            #print(f"MaxX: {maxx} MaxY: {maxy} MaxZ: {maxz} MinX: {minx} MinY: {miny} MinZ: {minz}")
            self.extents.append([maxx, maxy, maxz])
            self.extents.append([minx, miny, minz])
            iff.exitChunk("BOX ")

            iff.exitForm("0001")
            iff.exitForm("EXBX")

            # Collision stuff
            if iff.enterForm("NULL", True):
                print("No collision data - bailing")
                self.collision = bytearray(0)
                iff.exitForm("NULL")
            else:
                col_data_length = iff.getCurrentLength() + 8
                col_form_name = iff.getCurrentName()
                self.collision = iff.read_misc(col_data_length)
                print(f"Collision form: {col_form_name} Len: {col_data_length}")

            #hardpoints
            iff.enterForm("HPTS", True, False)
            while iff.enterChunk("HPNT", True):
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
                self.hardpoints.append([rotXx, rotXy, rotXz, posX, rotYx, rotYy, rotYz, posY, rotZx, rotZy, rotZz, posZ, hpntName])
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
            if version == "0001":
                iff.enterForm(version)
                iff.enterChunk("INFO")
                iff.exitChunk("INFO")

                iff.enterForm("VTXA")
                iff.enterForm("0003")

                iff.enterChunk("INFO")
                bit_flag = iff.read_int32()
                self.debug_flags(bit_flag, sps_no)
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
                print(f"SPS {sps_no} Shader: {sht} Version: {version}")

                sps = SPS(sps_no, sht, bit_flag, verts, indexes)

                self.spss.append(sps)

            else:
                print(f"Warning: Unknown SPS {sps_no} Unhandled version: {version}")
                
            iff.exitForm()

        return True
            
    def write(self, filename):
        iff = nsg_iff.IFF(initial_size=10000)
        # - BEGIN MESH        
        iff.insertForm("MESH")
        iff.insertForm("0005")

        # -- BEGIN APPR
        iff.insertForm("APPR")
        iff.insertForm("0003")

        # --- BEGIN EXTENTS
        iff.insertForm("EXBX")
        iff.insertForm("0001")
        iff.insertForm("EXSP")
        iff.insertForm("0001")

        iff.insertChunk("SPHR")
        
        diff_x = math.fabs(self.extents[0][0]) + math.fabs(self.extents[1][0])
        diff_y = math.fabs(self.extents[0][1]) + math.fabs(self.extents[1][1])
        diff_z = math.fabs(self.extents[0][2]) + math.fabs(self.extents[1][2])
        
        center_x = self.extents[1][0] + (diff_x/2)
        center_y = self.extents[1][1] + (diff_y/2)
        center_z = self.extents[1][2] + (diff_z/2)
        rad = (max(diff_x, diff_y, diff_z)/2)

        iff.insertFloatVector3((center_x, center_y, center_z))
        iff.insertFloat(rad)
        iff.exitChunk("SPHR")
        iff.exitForm(("0001"))
        iff.exitForm("EXSP")

        iff.insertChunk("BOX ")
        iff.insertFloatVector3(self.extents[0])
        iff.insertFloatVector3(self.extents[1])
        iff.exitChunk("BOX ")

        iff.exitForm("0001")
        iff.exitForm("EXBX")
        # --- END EXTENTS

        # --- BEGIN COLLISION
        if self.collision == None or len(self.collision) == 0 :
            iff.insertForm("NULL")
        else :
            iff.insertForm(self.collision[8:12].decode('ASCII'))
            iff.insertIffData(self.collision[12:])
        iff.exitForm()
        # --- END COLLISION

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

        # -- BEGIN APPR
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
            iff.insert_uint32(4357)
            iff.insert_uint32(len(sps.verts))
            iff.exitChunk("INFO")
            iff.insertChunk("DATA")
            for v in sps.verts:
                iff.insertFloatVector3((v.pos.x, v.pos.y, v.pos.z))
                iff.insertFloatVector3((v.normal.x, v.normal.y, v.normal.z))
                if len(v.texs) > 0 and (len(v.texs[0]) > 0):
                    iff.insertFloatVector2((v.texs[0][0], v.texs[0][1]))
                else:                    
                    iff.insertFloatVector2((0,0))
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