import bpy
import os
import shutil

# Set base output directory
base_dir = "/home/teng_guo/test_blender/daes"
world_name = "scene"
models_dir = os.path.join(base_dir, "models")
os.makedirs(models_dir, exist_ok=True)

# Use STL by default (DAE is failing)
use_stl = True

# Ensure Object Mode
if bpy.ops.object.mode_set.poll():
    bpy.ops.object.mode_set(mode='OBJECT')

# World XML init
world_xml = [
    '<?xml version="1.0" ?>',
    '<sdf version="1.6">',
    f'  <world name="{world_name}">'
]

# Deselect all
bpy.ops.object.select_all(action='DESELECT')

# Process each mesh object
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue

    # Validate mesh
    model_name = obj.name
    if len(obj.data.polygons) == 0:
        print(f"Error: {model_name} has no faces, skipping export.")
        continue

    # Select and clean mesh
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.quads_convert_to_tris()  # Force triangulation
    bpy.ops.mesh.delete_loose()  # Remove loose vertices/edges
    bpy.ops.mesh.fill_holes()  # Fill holes to ensure manifold
    bpy.ops.object.mode_set(mode='OBJECT')

    # Prepare model folder
    model_folder = os.path.join(models_dir, model_name)
    mesh_folder = os.path.join(model_folder, "meshes")
    tex_folder = os.path.join(model_folder, "materials", "textures")
    os.makedirs(mesh_folder, exist_ok=True)
    os.makedirs(tex_folder, exist_ok=True)

    # Temporarily rotate for Y-up (Gazebo)
    original_rotation = obj.rotation_euler.copy()
    obj.rotation_euler = (0, 0, 0)
    obj.rotation_euler[0] = -1.570796  # -90 degrees around X
    bpy.context.view_layer.update()

    # Export mesh (STL or DAE)
    mesh_path = os.path.join(mesh_folder, f"{model_name}.{'stl' if use_stl else 'dae'}")
    mesh_uri = f"model://{model_name}/meshes/{model_name}.{'stl' if use_stl else 'dae'}"
    print(f"Exporting to: {mesh_path}")
    try:
        if use_stl:
            bpy.ops.export_mesh.stl(filepath=mesh_path, use_selection=True)
        else:
            bpy.ops.wm.collada_export(
                filepath=mesh_path,
                selected=True,
                triangulate=True,
                use_object_instantiation=False,
                use_blender_profile=True,
                sort_by_name=True,
                keep_bind_info=False,
                apply_global_orientation=True
            )
        if not os.path.exists(mesh_path):
            print(f"Error: Failed to create {mesh_path}, skipping {model_name}.")
            continue
    except Exception as e:
        print(f"Error exporting {model_name}: {e}")
        continue

    # Restore rotation
    obj.rotation_euler = original_rotation
    bpy.context.view_layer.update()

    # Handle textures and materials (skip for STL)
    material_script = ""
    material_name = f"{model_name}_material"
    texture_files = []
    if not use_stl:
        for mat in obj.data.materials or []:
            if mat and mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        img = node.image
                        if img and img.filepath:
                            img_path = bpy.path.abspath(img.filepath)
                            if os.path.exists(img_path):
                                tex_name = os.path.basename(img_path)
                                dst = os.path.join(tex_folder, tex_name)
                                try:
                                    shutil.copy(img_path, dst)
                                    texture_files.append(tex_name)
                                except Exception as e:
                                    print(f"Error copying texture {tex_name}: {e}")

        if texture_files:
            material_script = f"""<material>
              <script>
                <uri>model://{model_name}/materials/textures</uri>
                <name>{material_name}</name>
              </script>
            </material>"""
            material_file = os.path.join(model_folder, "materials", f"{model_name}.material")
            with open(material_file, 'w') as f:
                f.write(f"""material {material_name}
{{
  technique
  {{
    pass
    {{
      texture_unit
      {{
        texture {texture_files[0]}
      }}
    }}
  }}
}}""")

    # Write model.config
    with open(os.path.join(model_folder, "model.config"), 'w') as f:
        f.write(f"""<?xml version="1.0"?>
<model>
  <name>{model_name}</name>
  <version>1.0</version>
  <sdf version="1.6">model.sdf</sdf>
  <author>
    <name>Blender Export</name>
    <email>noreply@example.com</email>
  </author>
  <description>Model of {model_name}</description>
</model>
""")

    # Write model.sdf
    with open(os.path.join(model_folder, "model.sdf"), 'w') as f:
        f.write(f"""<?xml version="1.0" ?>
<sdf version="1.6">
  <model name="{model_name}">
    <static>true</static>
    <link name="link">
      <visual name="visual">
        {material_script}
        <geometry>
          <mesh>
            <uri>{mesh_uri}</uri>
          </mesh>
        </geometry>
      </visual>
      <collision name="collision">
        <geometry>
          <mesh>
            <uri>{mesh_uri}</uri>
          </mesh>
        </geometry>
      </collision>
    </link>
  </model>
</sdf>
""")

    # Add to world XML
    world_xml.append(f"""    <include>
      <uri>model://{model_name}</uri>
      <name>{model_name}</name>
    </include>""")

# Close world file
world_xml.append("  </world>")
world_xml.append("</sdf>")

# Write .world file
world_path = os.path.join(base_dir, f"{world_name}.world")
with open(world_path, 'w') as f:
    f.write('\n'.join(world_xml))

print(f"Gazebo world written to: {world_path}")
print(f"Add to GAZEBO_MODEL_PATH: export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:{models_dir}")
print("Verify GAZEBO_MODEL_PATH is set:")
print("Run: echo $GAZEBO_MODEL_PATH")
