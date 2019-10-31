#Most credit goes to Jandals @ https://github.com/Jandals


bl_info = {
    "name": "",
    "author": "",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "Properties > Particle",
    "description": "",
    "warning": "",
    "wiki_url": "",
    "category": "",
}
    

import bpy

from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       EnumProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Menu,
                       Operator,
                       PropertyGroup,
                       Object,
                       )
from enum import Enum


#----------------------------------------------------------------------------------------
#                                   Helper functions
#----------------------------------------------------------------------------------------
class FormType(Enum):
    CONE = 0
    TUBE = 1
    SPIKE = 2
    CARD = 3



def getSeams(obj):
    seams = []
    for edge in obj.data.edges:
        if edge.use_seam:
            seams.append(edge)
    return seams #array of edge objects



def getTris(obj):
    faces = obj.data.polygons
    tris = []
    for face in faces:
        if len(face.edge_keys) == 3:
            tris.append(face.index)
    return tris #array of face indices



def getCoordinates(obj, vertIndex):
    return obj.data.vertices[vertIndex].co #vector



def getWorldCoordinate(obj, co):
    mat = obj.matrix_world
    loc = mat * co
    return loc #vector



def getLoops(obj, sepObj):
    sepVert, sepEdge, sepFace = sepObj
    formType = getHairFormType(obj, sepObj)
    edgesWithVerts = dict([(v.index, []) for v in obj.data.vertices])
    
    for e in obj.data.edges:
        for v in e.vertices:
            if e not in edgesWithVerts[v]:
                edgesWithVerts[v].append(e)
        
    seams = getSeams(obj)
    loopVerts = [[] for ob in formType]
    print(len(formType))
    for i in range(len(formType)):
        objSeams = [e for e in seams if e.index in sepEdge[i]]
        for edge in objSeams:
            for vert in edge.vertices:
                if [vert] not in loopVerts[i]:
                    loopVerts[i].append([vert])
                    
        while True:
            loopVertsSize = sum(len(x) for x in loopVerts[i])
            loopsN = len(loopVerts[i])
            for loop in range(loopsN):
                loopEndVert = loopVerts[i][loop][-1]
                for edge in edgesWithVerts[loopEndVert]:
                    vertInLoops = False
                    for vert in edge.vertices:
                        if vert == loopEndVert:
                            continue
                        else:
                            for loopToCheck in loopVerts[i]:
                                for vertToCheck in loopToCheck:
                                    if vert == vertToCheck:
                                        vertInLoops = True
                                        break
                                if vertInLoops:
                                    break
                            if not vertInLoops:
                                loopVerts[i][loop].append(vert)
                                break
                    if not vertInLoops:
                        break
            if loopVertsSize == sum(len(x) for x in loopVerts[i]):
                break
        
        tempLoopVerts = loopVerts[:]
        if (formType[i] == FormType.CONE) or (formType[i] == FormType.SPIKE):
            for j in range(1, len(loopVerts[i])):
                loopVerts[i][j].append(loopVerts[i][0][-1])
            
    return loopVerts #array of vertex index arrays
#import sys
#sys.path.append(r'C:\Users\Sunlitazure\Documents\Sunlitazure\projects\pony OC\scripts\Blender-Hairifier')
#import HairAddon
#from HairAddon import getLoops, separateObj

#from importlib import reload
#reload(HairAddon)
#from HairAddon import getLoops, separateObj



def separateObj(obj):
    vertices = []
    edges = []
    
    while True:
        newObj = False
        for v in obj.data.vertices:
            contained = False
            for o in vertices:
                if v.index in o:
                    contained = True
                    break
            if not contained:
                refVert = 0
                refObj = len(vertices)
                vertices.append([v.index])
                edges.append([])
                newObj = True
                break
            
        if not newObj:
           break
        
        added = True
        while added:
            added = False
            for e in obj.data.edges:
                for v in e.vertices:
                    if (vertices[refObj][refVert] == v) and (e.index not in edges[refObj]):
                        edges[refObj].append(e.index)
                        added = True
                        
            for e in edges[refObj]:
                for v in obj.data.edges[e].vertices:
                    if v not in vertices[refObj]:
                        vertices[refObj].append(v)
                        added = True
            
            if added:
                refVert = refVert + 1
                
        
        faces = [[f.index for f in obj.data.polygons if f.vertices[0] in v] for v in vertices]
    
    return vertices, edges, faces



def getHairFormType(obj, sepObj):
    sepVert, sepEdge, sepFace = sepObj
    allSeams = getSeams(obj)
    seams = [[e for e in allSeams if e.vertices[0] in v] for v in sepVert]
    seamVerts = [[] for ob in seams]
    loop = [False for ob in seams]
    
    for i in range(len(seams)):
        sharedVerts = 0
        for e in seams[i]:
            for v in e.vertices:
                if v not in seamVerts[i]:
                    seamVerts[i].append(v)
                elif v in seamVerts[i]:
                    sharedVerts = sharedVerts + 1
        if sharedVerts == len(seamVerts[i]):
            loop[i] = True
        
        allTris = getTris(obj)
        tris = [[f for f in allTris if f in sf] for sf in sepFace]
        
        forms = [None for ob in seams]
        
        for i in range(len(tris)):
            if len(tris[i]) == 0:
                if loop[i]:
                    forms[i] = FormType.TUBE
                else:
                    forms[i] = FormType.CARD
            elif len(tris[i]) > 0:
                if loop[i]:
                    forms[i] = FormType.CONE
                else:
                    forms[i] = FormType.SPIKE
        
        return forms



#CREDIT: dvochin @ https://www.blender.org/forum/viewtopic.php?p=105783#105783
def AssembleOverrideContextForView3dOps():
    #=== Iterates through the blender GUI's windows, screens, areas, regions to find the View3D space and its associated window.  Populate an 'oContextOverride context' that can be used with bpy.ops that require to be used from within a View3D (like most addon code that runs of View3D panels)
    # Tip: If your operator fails the log will show an "PyContext: 'xyz' not found".  To fix stuff 'xyz' into the override context and try again!
    for oWindow in bpy.context.window_manager.windows:          ###IMPROVE: Find way to avoid doing four levels of traversals at every request!!
        oScreen = oWindow.screen
        for oArea in oScreen.areas:
            if oArea.type == 'VIEW_3D':                         ###LEARN: Frequently, bpy.ops operators are called from View3d's toolbox or property panel.  By finding that window/screen/area we can fool operators in thinking they were called from the View3D!
                for oRegion in oArea.regions:
                    if oRegion.type == 'WINDOW':                ###LEARN: View3D has several 'windows' like 'HEADER' and 'WINDOW'.  Most bpy.ops require 'WINDOW'
                        #=== Now that we've (finally!) found the damn View3D stuff all that into a dictionary bpy.ops operators can accept to specify their context.  I stuffed extra info in there like selected objects, active objects, etc as most operators require them.  (If anything is missing operator will fail and log a 'PyContext: error on the log with what is missing in context override) ===
                        oContextOverride = {'window': oWindow, 'screen': oScreen, 'area': oArea, 'region': oRegion, 'scene': bpy.context.scene, 'edit_object': bpy.context.edit_object, 'active_object': bpy.context.active_object, 'selected_objects': bpy.context.selected_objects}   # Stuff the override context with very common requests by operators.  MORE COULD BE NEEDED!
                        #print("-AssembleOverrideContextForView3dOps() created override context: ", oContextOverride)
                        return oContextOverride
    raise Exception("ERROR: AssembleOverrideContextForView3dOps() could not find a VIEW_3D with WINDOW region to create override context to enable View3D operators.  Operator cannot function.")




#-----------------------------------------------------------------------
#                         Operators
#-----------------------------------------------------------------------
class GrowHair(Operator):
    bl_label = "Style Hair" #text on the button
    bl_idname = "particle.hair_style" #variable for calling operator
    bl_options = {'REGISTER', 'UNDO'} #register to display info in windows and support redo
    bl_description = "Grow hair guides from object" #tooltip
    
    @classmethod
    def poll(self, context):
        return(context.mode == 'OBJECT')
    
    def execute(self, context):
        partSys = context.object.particle_systems
        activeSys = partSys[partSys.active_index]
        hairStyle = activeSys.settings.hairStyle
        
        activeSysData = bpy.data.particles[partSys[partSys.active_index].settings.name]
        try:
            sepObj = separateObj(hairStyle.hairForm)
            loops = getLoops(hairStyle.hairForm, sepObj)
            
            for i in range(len(loops)-1):
                length = len(loops[i])
                length2 = len(loops[i+1])
                if length != length2:
                    self.report({'ERROR'}, 'all sides of hair form must have the same length')
                
            
        except AttributeError:
            self.report({'ERROR'}, "Hair form must be mesh object with seams marked where the hair roots start")
            
        guidesN = len(loops)
        guideSeg = len(loops[0])
        
        bpy.ops.particle.edited_clear()
        
        activeSysData.count = guidesN
        activeSysData.hair_step = guideSeg - 1
        activeSysData.display_step = 4
        
        bpy.ops.particle.particle_edit_toggle()
        bpy.context.scene.tool_settings.particle_edit.tool = 'COMB'
        contextOveride = AssembleOverrideContextForView3dOps()
        bpy.ops.particle.brush_edit(contextOveride, stroke=[{'name':'', 'location':(0,0,0), 'mouse':(0,0), 'pressure':0, 'size':0, 'pen_flip':False, 'time':0, 'is_start':False}])
        bpy.ops.particle.particle_edit_toggle()
        
        context.scene.tool_settings.particle_edit.use_emitter_deflect = False
        context.scene.tool_settings.particle_edit.use_preserve_root = False
        context.scene.tool_settings.particle_edit.use_preserve_length = False
        
        depsgraph = context.evaluated_depsgraph_get()
        depObj = context.object.evaluated_get(depsgraph)
        depPSys = depObj.particle_systems[partSys.active_index]
        
        for loop in range(len(loops)):
            part = depPSys.particles[loop]  
            part.location = hairStyle.hairForm.data.vertices[loops[loop][0]].co
            for vert in range(len(loops[loop])):
                part.hair_keys[vert].co = hairStyle.hairForm.data.vertices[loops[loop][vert]].co
                
        bpy.ops.particle.particle_edit_toggle()
        bpy.ops.particle.particle_edit_toggle()
        return {'FINISHED'}
    


#-----------------------------------------------------------------------
#          GUI Panel in ParticleSettings Properties Menu
#-----------------------------------------------------------------------
#GUI panel for addon found in properties -> particles (that's set to hair)
class HairAddonPanel(Panel):
    """Creates a panel in the Particles properties window"""
    
    bl_label = "Hair Addon"
    bl_idname = "OBJECT_PT_hairAddon"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "particle"
    
    @classmethod
    def poll(cls, context):
        partSys = context.object.particle_systems
        if len(partSys):
            return partSys[partSys.active_index].settings.type == "HAIR"
        else:
            return 0
    
    def draw(self, context):
        partSys = context.object.particle_systems
        layout = self.layout
        
        hairStyle = partSys[partSys.active_index].settings.hairStyle
        
        row = layout.row()
        row.label(text="add hair form")
        
        row = layout.row()
        row.prop(hairStyle, "hairForm", text="Hair Form")
        
        row = layout.row()
        row.operator("particle.hair_style")



#-----------------------------------------------------------------------
#                    Hair System variables
#-----------------------------------------------------------------------
class PartSettingsProperties(PropertyGroup):
    hairForm: PointerProperty(
        type = Object
        )



#-----------------------------------------------------------------------
#                         Registration
#-----------------------------------------------------------------------
classes = (
    PartSettingsProperties,
    GrowHair,
    HairAddonPanel,
)



def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.ParticleSettings.hairStyle = PointerProperty(type=PartSettingsProperties)
        
    
def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.ParticleSettings.hairStyle

if __name__ == "__main__":
    register()        
    
    


#bpy.data.particles['
#bpy.context.object.particle_systems['

#import sys
#sys.path.append(r'C:\Users\Sunlitazure\Documents\Sunlitazure\projects\pony OC\scripts\Blender-Hairifier')
#import HairAddon
#from HairAddon import getSeams

#from importlib import reload
#reload(HairAddon)
#from HairAddon import getSeams