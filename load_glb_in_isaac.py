from pxr import UsdPhysics, PhysxSchema
import omni.usd
import time

def get_all_children(prim):
    children = []
    def recurse(p):
        for child in p.GetChildren():
            children.append(child)
            recurse(child)
    recurse(prim)
    return children

def main():
    glb_path = "/home/ia/works/fbx/house_00000.glb"
    prim_path = "/World/house"

    stage = omni.usd.get_context().get_stage()

    from omni.isaac.core.utils.stage import add_reference_to_stage
    add_reference_to_stage(glb_path, prim_path)

    time.sleep(1.0)

    root_prim = stage.GetPrimAtPath(prim_path)
    if not root_prim or not root_prim.IsValid():
        print(f"ERROR: Prim at {prim_path} not found or invalid!")
        return



    for prim in get_all_children(root_prim):
        if prim.GetTypeName() == "Mesh":
            UsdPhysics.CollisionAPI.Apply(prim)
            PhysxSchema.PhysxCollisionAPI.Apply(prim)
            print(f"Collision enabled for: {prim.GetPath()}")

if __name__ == "__main__":
    main()
