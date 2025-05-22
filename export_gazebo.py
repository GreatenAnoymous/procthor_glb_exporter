import bpy
import os
import shutil
import re

# Output directory
output_dir = "/home/ia/works/worlds/"
os.makedirs(output_dir, exist_ok=True)

# Sanitize names for Windows
def sanitize_name(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name)

# Switch to Solid mode to suppress GPUTexture errors
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'SOLID'

# Switch to object mode
if bpy.ops.object.mode_set.poll():
    bpy.ops.object.mode_set(mode='OBJECT')

# Initialize world XML
world_xml = [
    '<?xml version="1.0" ?>',
    '<sdf version="1.6">',
    '  <world name="default">'
]
# Add default light and physics elements for Gazebo compatibility
world_xml.extend([
    '    <include>',
    '      <uri>model://sun</uri>',
    '    </include>',
        '    <light name="direct_light" type="directional">',
    '      <cast_shadows>true</cast_shadows>',
    '      <pose>0 10 10 0 0 0</pose>',
    '      <diffuse>1 1 1 1</diffuse>',
    '      <specular>0.1 0.1 0.1 1</specular>',
    '      <attenuation>',
    '        <range>1000</range>',
    '        <constant>0.9</constant>',
    '        <linear>0.01</linear>',
    '        <quadratic>0.001</quadratic>',
    '      </attenuation>',
    '      <direction>-0.5 -1 -1</direction>',
    '    </light>',
    '    <physics name="default_physics" default="0" type="ode">',
    '      <max_step_size>0.001</max_step_size>',
    '      <real_time_factor>1</real_time_factor>',
    '      <real_time_update_rate>1000</real_time_update_rate>',
    '    </physics>'
])

# Deselect all
bpy.ops.object.select_all(action='DESELECT')

# Debug: Print all images
print("Listing all images in the file:")
for img in bpy.data.images:
    print(f"Image: {img.name}, Filepath: {img.filepath}, Packed: {img.packed_file}, Has Data: {img.has_data}, Users: {img.users}")

# Export loop
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue

    safe_name = sanitize_name(obj.name)
    model_dir = os.path.join(output_dir, safe_name)
    os.makedirs(model_dir, exist_ok=True)
    print(f"\nProcessing object: {safe_name}")

    # Select object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Export textures
    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if not mat or not mat.use_nodes:
            print(f"Skipping material slot {mat_slot.name}: No material or nodes")
            continue

        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                image = node.image
                print(f"Found image: {image.name}, Packed: {image.packed_file}, Filepath: {image.filepath}, Has Data: {image.has_data}, Users: {image.users}")

                # Skip if no image data
                if not image.has_data:
                    print(f"⚠ Skipping {image.name}: No image data")
                    if image.filepath and os.path.exists(image.filepath):
                        try:
                            # Copy external file as fallback
                            filename = os.path.basename(image.filepath)
                            tex_path = os.path.join(model_dir, filename)
                            shutil.copy(image.filepath, tex_path)
                            print(f"✓ Copied external texture to: {tex_path}")
                            # Update node to reference copied file
                            node.image.filepath = tex_path
                        except Exception as e:
                            print(f"⚠ Failed to copy {filename}: {e}")
                    else:
                        print(f"⚠ Cannot process {image.name}: Filepath {image.filepath} does not exist")
                    continue

                # Determine file extension
                original_ext = os.path.splitext(image.name)[1].lower()
                if original_ext in {'.jpg', '.jpeg'}:
                    filename = sanitize_name(os.path.splitext(image.name)[0]) + '.jpg'
                    file_format = 'JPEG'
                else:
                    filename = sanitize_name(os.path.splitext(image.name)[0]) + '.png'
                    file_format = 'PNG'

                tex_path = os.path.join(model_dir, filename)
                print(f"Attempting to save texture to: {tex_path}")

                # Handle packed images
                if image.packed_file:
                    try:
                        # Save packed image directly
                        image.filepath_raw = tex_path
                        image.file_format = file_format
                        image.save()
                        print(f"✓ Saved packed texture: {tex_path}")
                        # Update node to reference saved file
                        node.image.filepath = filename
                    except Exception as e:
                        print(f"⚠ Failed to save packed texture {filename}: {e}")
                        continue
                else:
                    # Handle external images
                    if image.filepath and os.path.exists(image.filepath):
                        try:
                            shutil.copy(image.filepath, tex_path)
                            print(f"✓ Copied external texture to: {tex_path}")
                            # Update node to reference copied file
                            node.image.filepath = filename
                        except Exception as e:
                            print(f"⚠ Failed to copy {filename}: {e}")
                            continue
                    else:
                        print(f"⚠ Cannot copy {image.name}: Filepath {image.filepath} does not exist")
                        continue

    # Export .obj and .mtl
    obj_path = os.path.join(model_dir, f"{safe_name}.obj")
    try:
        bpy.ops.export_scene.obj(
            filepath=obj_path,
            use_selection=True,
            use_materials=True,
            axis_forward='-Z',
            axis_up='Y'
        )
        print(f"✓ Exported {safe_name} to {obj_path}")
    except Exception as e:
        print(f"⚠ Failed to export OBJ {safe_name}: {e}")

    # Fix .mtl texture paths to be relative
    mtl_path = os.path.join(model_dir, f"{safe_name}.mtl")
    if os.path.exists(mtl_path):
        try:
            with open(mtl_path, 'r') as f:
                lines = f.readlines()

            filtered_lines = []
            for line in lines:
                # Keep only lines related to material definition, Kd and map_Kd
                if line.startswith('newmtl') or line.startswith('Kd') or line.startswith('map_Kd'):
                    filtered_lines.append(line)
            
            with open(mtl_path, 'w') as f:
                f.writelines(filtered_lines)

            print(f"✓ Cleaned .mtl file for Gazebo: {mtl_path}")
        except Exception as e:
            print(f"⚠ Failed to clean .mtl file {mtl_path}: {e}")

    # Write model.sdf
    model_sdf = f"""<sdf version="1.6">
  <model name="{safe_name}">
    <static>true</static>
    <link name="link">
      <pose>0 0 0 0 0 0</pose>
      <visual name="visual">
        <geometry>
          <mesh>
            <uri>model://{safe_name}/{safe_name}.obj</uri>
          </mesh>
        </geometry>
      </visual>
      <collision name="collision">
        <geometry>
          <mesh>
            <uri>model://{safe_name}/{safe_name}.obj</uri>
          </mesh>
        </geometry>
      </collision>
    </link>
  </model>
</sdf>"""
    try:
        with open(os.path.join(model_dir, "model.sdf"), "w") as f:
            f.write(model_sdf)
        print(f"✓ Wrote model.sdf for {safe_name}")
    except Exception as e:
        print(f"⚠ Failed to write model.sdf for {safe_name}: {e}")

    # Write model.config
    model_config = f"""<?xml version="1.0" ?>
<model>
  <name>{safe_name}</name>
  <version>1.0</version>
  <sdf version="1.6">model.sdf</sdf>
  <author>
    <name>Blender Export</name>
  </author>
</model>"""
    try:
        with open(os.path.join(model_dir, "model.config"), "w") as f:
            f.write(model_config)
        print(f"✓ Wrote model.config for {safe_name}")
    except Exception as e:
        print(f"⚠ Failed to write model.config for {safe_name}: {e}")

    # Add to world
    world_xml.append(f"""    <include>
      <uri>model://{safe_name}</uri>
      <pose>0 0 0 1.5707963 0 0</pose>
    </include>""")

# Finish world
world_xml.append("  </world>")
world_xml.append("</sdf>")

# Write world file
world_path = os.path.join(output_dir, "scene.world")
try:
    with open(world_path, "w") as f:
        f.write("\n".join(world_xml))
    print(f"✓ Gazebo world file written to {world_path}")
except Exception as e:
    print(f"⚠ Failed to write world file {world_path}: {e}")

# Debug: Print images after processing
print("\nListing all images after processing:")
for img in bpy.data.images:
    print(f"Image: {img.name}, Filepath: {img.filepath}, Packed: {img.packed_file}, Has Data: {img.has_data}, Users: {img.users}")
