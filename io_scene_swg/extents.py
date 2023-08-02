from . import nsg_iff
from . import vector3D




class Extents():
    def __init__(self):
        pass

    def create(iff):
        tag = iff.getCurrentName()

        if tag == "NULL":
            print(f"Adding NULL extent")
            iff.enterAnyForm()
            iff.exitForm()
            return None
        elif tag == "EXSP":
            print(f"Adding EXSP extent")
            return SphereExtents.create(iff)
        elif tag == "EXBX":
            print(f"Adding EXBX extent")
            return BoxExtents.create(iff)
        elif tag == "CMPT":
            return ComponentExtent.create(iff)
        elif tag == "CPST":
            return CompositeExtent.create(iff)
        else:
            print(f"Unhandled extent type: {tag}")

        return None

class BoxExtents(Extents):
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
        print(f"Min: {min} Max: {max}")
        iff.exitChunk("BOX ")
        iff.exitForm("0001")
        iff.exitForm("EXBX")
        return BoxExtents(min, max)

    def getCenter(self):
        mag = (self.max - self.min) 
        vec =  vector3D.Vector3D(mag.x/2, mag.y/2, mag.z/2) + self.min
        return [vec.x,vec.y,vec.z]

    def getSize(self):
        return [(self.max.x - self.min.x)/2, (self.max.y - self.min.y)/2, (self.max.z - self.min.z)/2]

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
        print(f"Center: {center} Radius: {radius}")
        iff.exitChunk("SPHR")
        iff.exitForm("0001")
        iff.exitForm("EXSP")
        return SphereExtents(center, radius)

# public class SphereExtents : Extents
# {
#     public Vector3 center;
#     public float radius;
#     Color color;

#     public static SphereExtents create(Iff iff)
#     {
#         iff.enterForm("EXSP");
#         iff.enterForm("0001");
#         iff.enterChunk("SPHR");
#         Vector3 center = new Vector3(iff.read_float(), iff.read_float(), iff.read_float());
#         float radius = iff.read_float();
#         Debug.LogFormat("Center: {0} Radius: {1}", center, radius);
#         iff.exitChunk("SPHR");
#         iff.exitForm("0001");
#         iff.exitForm("EXSP");
#         SphereExtents e = new SphereExtents(center, radius, Color.yellow);
#         return e;
#     }
#     public SphereExtents(Vector3 center, float r, Color color)
#     {
#         this.center = center;
#         this.radius = r;
#         this.color = color;
#     }
#     public override void DrawGizmos(Transform parent)
#     {
#         Color old = Gizmos.color;
#         Gizmos.color = color;
#         Gizmos.DrawWireSphere(parent.TransformPoint(center), radius);
#         Gizmos.color = old;
#     }

#     public override void AddToGameObject(GameObject go)
#     {
#         SphereCollider c = go.AddComponent<SphereCollider>();
#         c.center = center;
#         c.radius = radius;
#     }
# }

# public class BoxExtents : Extents
# {
#     public Vector3 min;
#     public Vector3 max;
#     public Color color;

#     public static BoxExtents create(Iff iff)
#     {
#         iff.enterForm("EXBX");
#         iff.enterForm("0001");

#         iff.enterForm("EXSP");
#         iff.exitForm("EXSP");

#         iff.enterChunk("BOX ");
#         Vector3 min = new Vector3(iff.read_float(), iff.read_float(), iff.read_float());
#         Vector3 max = new Vector3(iff.read_float(), iff.read_float(), iff.read_float());
#         Debug.LogFormat("Min: {0} Max: {1}", min, max);
#         iff.exitChunk("BOX ");
#         iff.exitForm("0001");
#         iff.exitForm("EXBX");
#         BoxExtents e = new BoxExtents(min, max, Color.blue);
#         return e;
#     }
#     public BoxExtents(Vector3 min, Vector3 max, Color color)
#     {
#         this.min = min;
#         this.max = max;
#         this.color = color;
#     }

#     public override void DrawGizmos(Transform parent)
#     {
#         Vector3 minWorld = parent.TransformPoint(min);
#         Vector3 maxWorld = parent.TransformPoint(max);
#         Vector3 size = new Vector3(Mathf.Abs(max.x - min.x) * parent.localScale.x, Mathf.Abs(max.y - min.y) * parent.localScale.y, Mathf.Abs(max.z - min.z) * parent.localScale.z);
#         Color old = Gizmos.color;
#         Gizmos.color = color;
#         Gizmos.DrawWireCube((minWorld + (maxWorld - minWorld) / 2), size );
#         Gizmos.color = old;
#     }

#     public override void AddToGameObject(GameObject go)
#     {
#         BoxCollider c = go.AddComponent<BoxCollider>();
#         c.center = (min + (max - min) / 2);
#         c.size = new Vector3(Mathf.Abs(max.x - min.x), Mathf.Abs(max.y - min.y), Mathf.Abs(max.z - min.z));
#     }
# }

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

# public class DetailExtent : Extents
# {
#     public CompositeExtent extent;

#     public static DetailExtent create(Iff iff)
#     {
#         DetailExtent e = new DetailExtent();
#         e.load(iff);
#         return e;
#     }
#     public DetailExtent()
#     {

#     }

#     public void load(Iff iff)
#     {
#         iff.enterForm("DTAL");
#         iff.enterForm("0000");
#         extent = CompositeExtent.create(iff);
#         iff.exitForm("0000");
#         iff.exitForm("DTAL");
#     }

#     public override void DrawGizmos(Transform parent)
#     {
#         if (extent != null)
#         {
#             extent.DrawGizmos(parent);
#         }
#     }

#     public override void AddToGameObject(GameObject go)
#     {
#         extent.AddToGameObject(go);
#     }
# }

# public class MeshExtent : Extents 
# {
#     public int[] triangles;
#     public Vector3[] verts;
#     IffClasses.IndexedTriangleListIFF tri;
#     public static MeshExtent create(Iff iff)
#     {
#         MeshExtent e = new MeshExtent();
#         e.load(iff);
#         return e;
#     }

#     public void load(Iff iff)
#     {
#         iff.enterForm("CMSH");
#         iff.enterForm("0000");
#         tri = new IffClasses.IndexedTriangleListIFF(iff);
#         tri.load(iff);
#         iff.exitForm("0000");
#         iff.exitForm("CMSH");
#     }
#     public MeshExtent()
#     {
#     }

#     public override void DrawGizmos(Transform parent)
#     {
#         //foreach (Extents e in extents)
#         //{
#         //    e.DrawGizmos(parent);
#         //}
#     }

#     public override void AddToGameObject(GameObject go)
#     {
#         tri.ToCollider(go);
#     }
# }

#     {
#         string tag = iff.getCurrentName();
#         Debug.Log("Creating collision shape: " + tag);
#         switch (tag)
#         {
#             case "NULL":
#                 iff.enterForm();
#                 iff.exitForm();
#                 return null;
#             case "EXSP":
#                 return SphereExtents.create(iff);
#             case "EXBX":
#                 return BoxExtents.create(iff);
#             case "CMPT":
#                 return ComponentExtent.create(iff);
#             case "CPST":
#                 return CompositeExtent.create(iff);
#             case "DTAL":
#                 return DetailExtent.create(iff);
#             case "CMSH":
#                 return MeshExtent.create(iff);
#             case "XOCL":
#             case "XCYL":
#             default:
#                 Debug.LogFormat("Unhandled Extent Type: {0}", iff.getCurrentName());
#                 break;
#         }
#         return null;
#     }
#     public static bool write(Iff iff, GameObject go, Transform origin = null)
#     {
#         Collider[] colliders = go.GetComponentsInChildren<Collider>();
#         if(colliders.Length == 0)
#         {
#             return writeNull(iff, origin);
#         }
#         else if(colliders.Length == 1)
#         {
#             BoxCollider box = colliders[0] as BoxCollider;
#             if(box != null)
#             {
#                 Debug.LogFormat("Writing a box: {0}", box.bounds);
#                 return writeBox(iff, box, origin);
#             }

#             SphereCollider sphere = colliders[0] as SphereCollider;
#             if(sphere != null)
#             {
#                 Debug.LogFormat("Writing a sphere: {0}", sphere.radius);
#                 return writeSphere(iff, sphere, origin);
#             }

#             MeshCollider mesh = colliders[0] as MeshCollider;
#             if (mesh != null)
#             {
#                 Debug.LogFormat("Writing a mesh: {0} tris", mesh.sharedMesh.triangles.Length);
#                 return writeMesh(iff, mesh, origin);
#             }
#             return false;
#         }
#         else
#         {
#             writeMultiple(iff, colliders);
#             Debug.LogFormat("Wrote Colliders: {0}", colliders.Length);
#             return true;
#         }
#     }

#     public static bool writeCollider(Iff iff, Collider col, Transform origin = null)
#     {
#         BoxCollider box = col as BoxCollider;
#         if (box != null)
#         {
#             return writeBox(iff, box, origin);
#         }

#         SphereCollider sphere = col as SphereCollider;
#         if (sphere != null)
#         {
#             return writeSphere(iff, sphere, origin);
#         }

#         MeshCollider mesh = col as MeshCollider;
#         if (mesh != null)
#         {
#             return writeMesh(iff, mesh, origin);
#         }
#         return false;
#     }
#     public static bool writeSphere(Iff iff, SphereCollider sphere, Transform origin = null)
#     {
#         if (sphere != null)
#         {
#             iff.insertForm("EXSP");
#             iff.insertForm("0001");
#             iff.insertChunk("SPHR");
#             Vector3 center = (origin != null) ? origin.InverseTransformPoint(sphere.center) : sphere.center;
#             iff.insertChunkFloatVector(new Vec3(center.x, center.y, center.z));
#             Debug.LogFormat("Wrote sphere center: {0} as {1}", sphere.center, center);
#             iff.insertFloat(sphere.radius);
#             iff.exitChunk("SPHR");
#             iff.exitForm("0001");
#             iff.exitForm("EXSP");
#             return true;
#         }
#         return false;
#     }
#     public static bool writeBox(Iff iff, BoxCollider box, Transform origin = null)
#     {
#         if(box != null)
#         {
#             iff.insertForm("EXBX");
#             iff.insertForm("0001");

#             iff.insertForm("EXSP");
#             iff.insertForm("0001");
#             iff.insertChunk("SPHR");
#             iff.insertChunkFloatVector(new Vec3(0,0,0));
#             iff.insertFloat(1);
#             iff.exitChunk("SPHR");
#             iff.exitForm("0001");
#             iff.exitForm("EXSP");

#             iff.insertChunk("BOX ");
#             //iff.insertChunkFloatVector(box.bounds.max);
#             //iff.insertChunkFloatVector(box.bounds.min);
#             Vector3 max = (origin != null) ? origin.InverseTransformPoint((box.size / 2) + box.center) : (box.size / 2) + box.center;
#             Vector3 min = (origin != null) ? origin.InverseTransformPoint(-(box.size / 2) + box.center) : -(box.size / 2) + box.center;
#             iff.insertChunkFloatVector(new Vec3(max.x, max.y, max.z));
#             iff.insertChunkFloatVector(new Vec3(min.x, min.y, min.z));
#             //iff.insertChunkFloatVector((box.size / 2) + box.center);
#             //iff.insertChunkFloatVector(-(box.size / 2) + box.center);
#             iff.exitChunk("BOX ");

#             iff.exitForm("0001");
#             iff.exitForm("EXBX");
#             return true;
#         }
#         return false;
#     }

#     public static bool writeMesh(Iff iff, MeshCollider mesh, Transform origin = null)
#     {
#         if (mesh != null)
#         {
#             iff.insertForm("CMSH");
#             iff.insertForm("0000");

#             Iff meshIff = new Iff(100);
#             IffClasses.IndexedTriangleListIFF tri = new IffClasses.IndexedTriangleListIFF(meshIff);
#             tri.FromCollider(mesh);
#             tri.write(meshIff);
#             iff.insertIff(meshIff);

#             iff.exitForm("0000");
#             iff.exitForm("CMSH");
#             return true;
#         }
#         return false;
#     }
#     public static bool writeMultiple(Iff iff, Collider[] colliders, Transform origin = null)
#     {
#         iff.insertForm("CMPT");
#         iff.insertForm("0000");
#         iff.insertForm("CPST");
#         iff.insertForm("0000");
#         foreach(Collider c in colliders)
#         {
#             writeCollider(iff, c, origin);
#         }
#         iff.exitForm("0000");
#         iff.exitForm("CPST");
#         iff.exitForm("0000");
#         iff.exitForm("CMPT");
#         return true;
#     }

#     static bool writeNull(Iff iff, Transform origin = null)
#     {
#         iff.insertForm("NULL");
#         Debug.LogWarning("Wrote NULL for extents because we didn't find anyw writable extents");
#         iff.exitForm("NULL");
#         return true;
#     }
# }
