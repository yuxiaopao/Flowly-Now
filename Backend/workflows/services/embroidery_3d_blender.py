"""Blender scene builder: reference curves, stitched surfaces and 3D garment morph."""
from __future__ import annotations

import argparse
import json
import math
import hashlib
from pathlib import Path

import bpy
from mathutils import Vector


def material(name, color, thread=False, cloth=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = .54 if thread else .8
    bsdf.inputs['Sheen Weight'].default_value = .08 if thread else .15
    bsdf.inputs['Specular IOR Level'].default_value = .2 if thread else .25
    if thread:
        bsdf.inputs['Anisotropic'].default_value = .7
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 450
        noise.inputs['Detail'].default_value = 3
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .24
        bump.inputs['Distance'].default_value = .002
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    if cloth:
        tex = nodes.new('ShaderNodeTexCoord')
        waves = []
        for direction in ('X', 'Y'):
            wave = nodes.new('ShaderNodeTexWave')
            wave.wave_type = 'BANDS'
            wave.bands_direction = direction
            wave.inputs['Scale'].default_value = SPEC['cloth']['weave_scale']
            wave.inputs['Distortion'].default_value = 1.6
            links.new(tex.outputs['Generated'], wave.inputs['Vector'])
            waves.append(wave)
        mix = nodes.new('ShaderNodeMath')
        mix.operation = 'MULTIPLY'
        links.new(waves[0].outputs['Fac'], mix.inputs[0])
        links.new(waves[1].outputs['Fac'], mix.inputs[1])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = SPEC['cloth']['bump_strength']
        bump.inputs['Distance'].default_value = SPEC['cloth']['bump_distance']
        links.new(mix.outputs[0], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def collection(name):
    item = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(item)
    return item


def mesh(name, vertices, faces, mat, group):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    group.objects.link(obj)
    obj.data.materials.append(mat)
    for polygon in data.polygons:
        polygon.use_smooth = True
    return obj


def curve(name, points, radius, mat, group):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 2
    data.bevel_depth = radius
    data.bevel_resolution = 2
    data.resolution_u = 4
    data.use_fill_caps = True
    spline = data.splines.new('POLY')
    spline.points.add(len(points)-1)
    for point, coordinate in zip(spline.points, points):
        point.co = (*coordinate, 1)
    obj = bpy.data.objects.new(name, data)
    group.objects.link(obj)
    data.materials.append(mat)
    return obj


def frame(t):
    return round(t * SPEC['fps']) + 1


def key(obj, prop, value, t):
    setattr(obj, prop, value)
    obj.keyframe_insert(data_path=prop, frame=frame(t))


def hide_between(obj, start, end=60):
    key(obj, 'hide_render', True, 0)
    key(obj, 'hide_render', False, start)
    if end < SPEC['duration']:
        key(obj, 'hide_render', True, end)


def front_depth(x, z):
    g = SPEC['garment']
    radial = math.sqrt(max(.15, 1-(x/.9)**2))
    return g['front_depth'] * radial + .009*math.sin(z*23+x*7) + .009*math.sin(x*32+z*4)


def garment_point(x, y, depth):
    g = SPEC['garment']
    angle = math.radians(g['embroidery_rotation'])
    xx = g['embroidery_x'] + (x*math.cos(angle)-y*math.sin(angle))*g['embroidery_scale']
    zz = g['embroidery_z'] + (x*math.sin(angle)+y*math.cos(angle))*g['embroidery_scale']
    return (xx, front_depth(xx, zz)-depth*g['embroidery_scale']-.009, zz)


def torso(mat, group):
    g = SPEC['garment']
    vertices, faces = [], []
    columns, rows = g['grid_columns'], g['grid_rows']
    for side in (-1, 1):
        offset = len(vertices)
        for j in range(rows+1):
            v = j/rows
            width = g['base_width'] * (1-.1*math.sin(v*math.pi)+.08*v*v)
            for i in range(columns+1):
                u = 2*i/columns-1
                x = width*u
                top = g['top']-.08*abs(u)-.07*max(0,1-(x/.24)**2)
                z = g['bottom']+(top-g['bottom'])*v
                y = front_depth(x, z) * (-side)
                vertices.append((x, y, z))
        for j in range(rows):
            for i in range(columns):
                a = offset+j*(columns+1)+i
                indices = (a, a+1, a+columns+2, a+columns+1)
                faces.append(indices if side == -1 else indices[::-1])
    panel = (rows+1)*(columns+1)
    # Join shoulder and side panels; leave a real neck opening and lower hem.
    for i in range(columns):
        x = vertices[rows*(columns+1)+i][0]
        if abs(x) > .24:
            a = rows*(columns+1)+i
            faces.append((a,a+1,a+1+panel,a+panel))
    for j in range(rows):
        for i in (0,columns):
            a = j*(columns+1)+i
            faces.append((a,a+columns+1,a+columns+1+panel,a+panel))
    obj = mesh('Jacket_front_and_back_cloth', vertices, faces, mat, group)
    solid = obj.modifiers.new('Real fabric thickness', 'SOLIDIFY')
    solid.thickness = .009
    subdiv = obj.modifiers.new('Smooth garment surface', 'SUBSURF')
    subdiv.levels = 1
    return obj


def sleeve(side, mat, group):
    g = SPEC['garment']
    verts, faces = [], []
    segments, rings = 48, 20
    origin = Vector((side*.56, .0, 2.27))
    axis = Vector((side*.58, .0, -.81)).normalized()
    across = Vector((0, 1, 0))
    perpendicular = axis.cross(across).normalized()
    for j in range(rings+1):
        t = j/rings
        center = origin + axis*g['sleeve_length']*t
        radius = g['sleeve_radius']*(1-.16*t)
        for i in range(segments):
            angle = 2*math.pi*i/segments
            rr = radius*(1+.016*math.cos(angle*7+j*.35))
            p = center+rr*(math.cos(angle)*across+math.sin(angle)*perpendicular)
            verts.append(tuple(p))
    for j in range(rings):
        for i in range(segments):
            a, b = j*segments+i, j*segments+(i+1)%segments
            faces.append((a, b, b+segments, a+segments))
    verts.append(tuple(origin))
    for i in range(segments):
        faces.append((len(verts)-1,(i+1)%segments,i))
    obj = mesh(f'Jacket_{side}_sleeve', verts, faces, mat, group)
    solid = obj.modifiers.new('Sleeve fabric thickness', 'SOLIDIFY')
    solid.thickness = .008
    return obj, origin, axis, across, perpendicular


def collar(mat, group):
    vertices, faces = [], []
    segments = 72
    for ring in range(2):
        for i in range(segments):
            angle = 2*math.pi*i/segments
            radius = .24+.022*ring
            vertices.append((math.cos(angle)*radius, math.sin(angle)*radius*1.08, 2.35+ring*.20))
    for i in range(segments):
        j = (i+1)%segments
        faces.append((i, j, j+segments, i+segments))
    obj = mesh('Standing_mandarin_collar', vertices, faces, mat, group)
    solid = obj.modifiers.new('Collar fabric thickness', 'SOLIDIFY')
    solid.thickness = .014
    return obj


def sphere(name, position, radius, mat, group):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=radius, location=position)
    obj = bpy.context.object
    obj.name = name
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
    group.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def geometry():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = SPEC['engine']
    scene.render.resolution_x = SPEC['width']
    scene.render.resolution_y = SPEC['height']
    scene.render.resolution_percentage = 100
    scene.render.fps = SPEC['fps']
    scene.frame_start = 1
    scene.frame_end = SPEC['duration']*SPEC['fps']
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.world.color = (.75, .75, .75)
    if hasattr(scene, 'eevee'):
        scene.eevee.taa_render_samples = SPEC['samples']
    thread_mats = {name: material(name, SPEC['colors'][name], thread=True) for name in ('indigo', 'slate', 'pearl')}
    linen = material('woven_linen', SPEC['colors']['linen'], cloth=True)
    ivory = material('ivory_garment', SPEC['colors']['garment'], cloth=True)
    bones, feathers, garments, stage = [collection(name) for name in ('Butterfly_bone', 'Phoenix_feather', 'Garment', 'Studio')]
    z = SPEC['board']['z']
    w, h = SPEC['board']['width']/2, SPEC['board']['height']/2
    mesh('Linen_hero_panel', [(-w,-h,z), (w,-h,z), (w,h,z), (-w,h,z)], [(0,1,2,3)], linen, stage)
    # Original image is a genuine flat plane. Three-dimensional paths replace it.
    plane = mesh('Original_flat_reference', [(-1.45,-1.02,z+.002), (1.45,-1.02,z+.002), (1.45,1.02,z+.002), (-1.45,1.02,z+.002)], [(0,1,2,3)], linen, stage)
    uv = plane.data.uv_layers.new()
    for polygon in plane.data.polygons:
        for i, loop in enumerate(polygon.loop_indices):
            uv.data[loop].uv = [(0,0),(1,0),(1,1),(0,1)][i]
    flat = bpy.data.materials.new('source_flat_drawing')
    flat.use_nodes = True
    flat_bsdf = flat.node_tree.nodes.get('Principled BSDF')
    texture = flat.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = bpy.data.images.load(str(DIRECTORY/'reference_motif.png'))
    flat.node_tree.links.new(texture.outputs['Color'], flat_bsdf.inputs['Base Color'])
    plane.data.materials.clear()
    plane.data.materials.append(flat)
    records = sorted(DATA['paths'], key=lambda row: (row['role'] != 'bone', sum(p[0]*p[0]+p[1]*p[1] for p in row['points'])/len(row['points'])))
    for i, row in enumerate(records):
        points = []
        for j, point in enumerate(row['points']):
            x,y = point[:2]
            loft = point[2] if len(point)>2 else SPEC['trace']['thread_height']
            if row['kind'] == 'satin' and len(point)<3:
                loft += SPEC['trace']['stitch_lift']*math.sin(math.pi*j/(len(row['points'])-1))
            points.append((x,y,z+loft))
        kind = row['kind']
        mat = thread_mats[row['color']]
        obj = curve(f'Thread_{i:04}_{row["role"]}_{kind}', points, SPEC['trace']['fill_radius'] if kind == 'satin' else SPEC['trace']['border_radius'], mat, bones if row['role'] == 'bone' else feathers)
        obj['role'] = row['role']
        obj['kind'] = kind
        obj['path_index'] = i
    # Disappearing angular outer boundaries explain the innovation explicitly.
    for sx in (-1, 1):
        for sy in (-1, 1):
            pts = [(0,0,z+.018),(sx*.62,sy*.18,z+.018),(sx*1.22,sy*.86,z+.018),(sx*.98,sy*.04,z+.018),(0,0,z+.018)]
            obj = curve(f'Closed_wing_boundary_{sx}_{sy}', pts, .004, thread_mats['pearl'], bones)
            obj['temporary_boundary'] = True
    torso(ivory, garments)
    collar(ivory, garments)
    sleeves = [sleeve(side, ivory, garments) for side in (-1,1)]
    seam_points = []
    for i in range(50):
        t = i/49
        x, zz = .22-.66*t, 2.37-.92*t
        seam_points.append((x,front_depth(x,zz)-.017,zz))
    curve('Diagonal_placket_binding', seam_points, .009, ivory, garments)
    for i in range(5):
        t = .08+i*.18
        x, zz = .22-.66*t, 2.37-.92*t
        yy = front_depth(x,zz)-.028
        sphere(f'Frog_button_{i}',(x,yy,zz),.025,ivory,garments)
        curve(f'Frog_button_loop_{i}',[(x-.035,yy,zz-.025),(x-.07,yy-.009,zz),(x-.035,yy,zz+.025)],.008,ivory,garments)
    cuffs = collection('Cuff_embroidery')
    for side, (_, origin, axis, across, perpendicular) in zip((-1,1),sleeves):
        for i,row in enumerate(records):
            pts=[]
            for coordinate in row['points']:
                x,y = coordinate[:2]
                t=.86+y*.08
                angle=-math.pi/2+x*.78
                radius=SPEC['garment']['sleeve_radius']*(1-.16*t)+.002+(coordinate[2]*.12 if len(coordinate)>2 else .005)
                point=origin+axis*SPEC['garment']['sleeve_length']*t+radius*(math.cos(angle)*across+math.sin(angle)*perpendicular)
                pts.append(tuple(point))
            obj=curve(f'Cuff_{side}_{i:04}',pts,.0018,thread_mats[row['color']],cuffs)
            obj['path_index']=i
    floor_mat=material('studio_paper',(.78,.77,.72,1))
    mesh('Studio_floor',[(-200,-200,.0),(200,-200,.0),(200,200,.0),(-200,200,.0)],[(0,1,2,3)],floor_mat,stage)
    for name,pos,energy,size in [('Key',(2,-3,7),900,5),('Fill',(-4,-1,4),500,4),('Rim',(2,4,5),650,3)]:
        data=bpy.data.lights.new(name,'AREA')
        data.energy,data.shape,data.size=energy,'DISK',size
        obj=bpy.data.objects.new(name,data)
        stage.objects.link(obj)
        obj.location=pos
        obj.rotation_euler=(Vector((0,0,1.5))-obj.location).to_track_quat('-Z','Y').to_euler()
    camera_data=bpy.data.cameras.new('Film_camera')
    camera=bpy.data.objects.new('Film_camera',camera_data)
    stage.objects.link(camera)
    camera_data.lens=45
    camera.location=(0,-3.6,6.3)
    camera.rotation_euler=(Vector((0,0,z))-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.camera=camera
    scene['reference_sha256']=DATA['reference_sha256']
    scene['source_line_paths']=DATA['line_paths']
    scene['actual_stitch_curves']=DATA['stitch_paths']
    scene['concept_disclosure']=SPEC['disclosure']
    bpy.ops.wm.save_as_mainfile(filepath=str(DIRECTORY/'scene.blend'))
    print(f'Created {DATA["stitch_paths"]} real 3D stitch paths',flush=True)


def export_glb(path, objects):
    bpy.ops.object.select_all(action='DESELECT')
    depsgraph=bpy.context.evaluated_depsgraph_get()
    copies=[]
    for obj in objects:
        if obj.type not in ('MESH','CURVE'):
            continue
        data=bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
        copy=bpy.data.objects.new(obj.name+'_export',data)
        bpy.context.scene.collection.objects.link(copy)
        copy.matrix_world=obj.matrix_world
        copy.select_set(True)
        copies.append(copy)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=False,export_apply=True)
    for obj in copies:
        data=obj.data
        bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.meshes.remove(data)


def animate():
    bpy.ops.wm.open_mainfile(filepath=str(DIRECTORY/'scene.blend'))
    scene=bpy.context.scene
    a=SPEC['animation']
    bones=[obj for obj in bpy.data.collections['Butterfly_bone'].objects if not obj.get('temporary_boundary')]
    feathers=list(bpy.data.collections['Phoenix_feather'].objects)
    for group,start,end in [(bones,a['bone_start'],a['bone_end']),(feathers,a['feather_start'],a['feather_end'])]:
        count=len(group)
        for index,obj in enumerate(group):
            onset=start+(end-start-1.2)*index/max(1,count-1)
            hide_between(obj,onset,a['mapping_start'])
            key(obj.data,'bevel_factor_end',0,onset)
            key(obj.data,'bevel_factor_end',1,onset+1.2)
            if obj.get('role')=='feather':
                pts=obj.data.splines[0].points
                cx=sum(p.co.x for p in pts)/len(pts)
                cy=sum(p.co.y for p in pts)/len(pts)
                key(obj,'location',(math.copysign(.22,cx),math.copysign(.12,cy),.07),a['feather_start'])
                key(obj,'location',(0,0,0),a['fusion_end'])
    for obj in bpy.data.collections['Butterfly_bone'].objects:
        if obj.get('temporary_boundary'):
            hide_between(obj,3,a['outline_delete_end'])
            key(obj.data,'bevel_factor_end',1,a['outline_delete_start'])
            key(obj.data,'bevel_factor_end',0,a['outline_delete_end'])
    hide_between(bpy.data.objects['Original_flat_reference'],0,a['flat_end'])
    hide_between(bpy.data.objects['Linen_hero_panel'],0,a['mapping_end'])
    for obj in bpy.data.collections['Garment'].objects:
        hide_between(obj,a['mapping_start'])
    cuff_objects=list(bpy.data.collections['Cuff_embroidery'].objects)
    for index,obj in enumerate(cuff_objects):
        onset=a['cuff_start']+(a['cuff_end']-a['cuff_start']-1)*index/max(1,len(cuff_objects)-1)
        hide_between(obj,onset)
        key(obj.data,'bevel_factor_end',0,onset)
        key(obj.data,'bevel_factor_end',1,onset+1)
    # Export actual curved geometry, before morphing it onto the garment.
    scene.frame_set(frame(a['mapping_start'])-1)
    export_glb(DIRECTORY/'pattern.glb',bones+feathers+[bpy.data.objects['Linen_hero_panel']])
    mapped=collection('Morphing_embroidery')
    depsgraph=bpy.context.evaluated_depsgraph_get()
    for obj in bones+feathers:
        data=bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
        moved=bpy.data.objects.new(obj.name+'_garment_morph',data)
        mapped.objects.link(moved)
        for vertex in data.vertices:
            vertex.co=obj.matrix_world@vertex.co
        moved.shape_key_add(name='Flat_3D_embroidery')
        conform=moved.shape_key_add(name='Garment_surface_mapping')
        for vertex in conform.data:
            x,y,z=vertex.co
            vertex.co=garment_point(x,y,z-SPEC['board']['z'])
        key(conform,'value',0,a['mapping_start'])
        key(conform,'value',1,a['mapping_end'])
        hide_between(moved,a['mapping_start'])
    camera=scene.camera
    camera_keys=[
        (0,(0,-4.5,7.5),(0,0,1.55),45),
        (6,(0,-4.5,7.3),(0,0,1.55),45),
        (14,(.35,-4.5,7.5),(0,0,1.55),45),
        (24,(-.6,-3.5,5.9),(0,0,1.55),45),
        (35,(.0,-4.3,7.4),(0,0,1.55),45),
        (38,(2.8,-4.8,6.5),(0,0,1.55),45),
        (41,(-2.8,-4.8,6.5),(0,0,1.55),45),
        (49,(.35,-3.8,2.7),(0,-.15,1.75),49),
        (53,(-1.0,-3.6,2.0),(-.6,-.1,1.65),46),
        (56,(1.0,-5.5,2.9),(0,0,1.5),45),
        (60,(2.0,-5.5,2.9),(0,0,1.5),45)
    ]
    for time,position,target,lens in camera_keys:
        key(camera,'location',position,time)
        camera.rotation_euler=(Vector(target)-Vector(position)).to_track_quat('-Z','Y').to_euler()
        camera.keyframe_insert(data_path='rotation_euler',frame=frame(time))
        key(camera.data,'lens',lens,time)
    scene.frame_set(frame(56))
    export_glb(DIRECTORY/'garment.glb',list(bpy.data.collections['Garment'].objects)+list(mapped.objects)+cuff_objects)
    scene.frame_set(1)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(DIRECTORY/'scene.blend'))
    report={'curve_objects':len(bones)+len(feathers),'garment_objects':len(bpy.data.collections['Garment'].objects),'morph_targets':len(mapped.objects),'frames':scene.frame_end,'fps':scene.render.fps,'reference_sha256':DATA['reference_sha256'],'actual_3d_geometry':True}
    (DIRECTORY/'scene_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)


def render(previews=False):
    bpy.ops.wm.open_mainfile(filepath=str(DIRECTORY/'scene.blend'))
    scene=bpy.context.scene
    if previews:
        scene.render.resolution_x=SPEC['preview_width']
        scene.render.resolution_y=SPEC['preview_height']
        if hasattr(scene,'eevee'):
            scene.eevee.taa_render_samples=SPEC['preview_samples']
        for t in SPEC['preview_times']:
            scene.frame_set(frame(t))
            scene.render.filepath=str(DIRECTORY/f'preview_{t:02d}.png')
            bpy.ops.render.render(write_still=True)
    else:
        destination=DIRECTORY/'frames'
        destination.mkdir(exist_ok=True)
        scene_hash=hashlib.sha256((DIRECTORY/'scene.blend').read_bytes()).hexdigest()
        manifest=destination/'scene_hash.txt'
        if any(destination.glob('*.png')) and (not manifest.exists() or manifest.read_text()!=scene_hash):
            raise RuntimeError('Existing frames belong to a different scene; use a new execution')
        manifest.write_text(scene_hash)
        for number in range(scene.frame_start,scene.frame_end+1):
            path=destination/f'{number:05d}.png'
            if path.exists():
                continue
            scene.frame_set(number)
            scene.render.filepath=str(path)
            bpy.ops.render.render(write_still=True)
            if number%SPEC['fps']==0:
                progress={'rendered_frames':number,'total_frames':scene.frame_end,'seconds':number/SPEC['fps']}
                progress_file=DIRECTORY/'render_progress.json'
                temporary=DIRECTORY/'render_progress.tmp'
                temporary.write_text(json.dumps(progress),encoding='utf-8')
                temporary.replace(progress_file)
                print(f'FILM_PROGRESS {number}/{scene.frame_end}',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--operation',choices=('build','animate','previews','render'),required=True)
    parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args(__import__('sys').argv[__import__('sys').argv.index('--')+1:])
    DIRECTORY=args.directory.resolve()
    DATA=json.loads((DIRECTORY/'geometry.json').read_text(encoding='utf-8'))
    SPEC=DATA['spec']
    {'build':geometry,'animate':animate,'previews':lambda:render(True),'render':render}[args.operation]()
