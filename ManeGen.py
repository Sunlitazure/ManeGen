# Most credit goes to Jandals @ https://github.com/Jandals


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
from mathutils import Vector
import random
from math import (sqrt,
                  floor,
                  acos,
                  asin,
                  cos,
                  sin,
                  pi
                  )
import numpy as np



#
#
# TODO: allow inverse distribution by increasing chance of selecting ref loops closer to loop
# TODO: Handle concave meshes
#       use average of loops on either side as the temp centerpoint, then move on to next n loops
#       after adding enough guides, replacing the og loop with the previous centerpoint.
#       ( (#loops/4) / guidesPerLoop ) = number of loops to move down for the next temp centerpoint
# TODO: Rename project to Blend_Salon or something
# TODO: Smooth out strip subdivision
# TODO: Make code readable
# TODO: refactor code so it doesn't suck anymore
#
#



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



def getLoops(obj, sepObj, formType):
    sepVert, sepEdge, sepFace = sepObj
    edgesWithVerts = dict([(v.index, []) for v in obj.data.vertices])
    
    for e in obj.data.edges:
        for v in e.vertices:
            if e not in edgesWithVerts[v]:
                edgesWithVerts[v].append(e)
        
    allSeams = getSeams(obj)
    seams = [[e for e in allSeams if e.vertices[0] in v] for v in sepVert]
    loopVerts = [[] for ob in formType]
    for i in range(len(loopVerts)):
        objSeams = seams[i]
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
    
    newLoopVerts = [[obj[0]] for obj in loopVerts]       
    for i in range(len(loopVerts)):
        if (formType[i] == FormType.CARD) or (formType[i] == FormType.SPIKE):
            for j in range(len(loopVerts[i])):
                if len(edgesWithVerts[loopVerts[i][j][0]]) < 3:
                    newLoopVerts[i][0] = loopVerts[i][j]
                    break
        
        for j in range(len(loopVerts[i])):
            for seam in seams[i]:
                if (newLoopVerts[i][-1][0] in seam.vertices) and (len(newLoopVerts[i]) < 2 or (newLoopVerts[i][-2][0] not in seam.vertices)):
                    for vert in seam.vertices:
                        if vert != newLoopVerts[i][-1][0]:
                            newVert = vert
                            break
                    for loop in loopVerts[i]:
                        if (loop[0] == vert) and (loop[0] != newLoopVerts[i][0][0]):
                            newLoopVerts[i].append(loop)
                            break
                        
            if len(newLoopVerts[i]) == len(loopVerts[i]):
                break
    
    loopVerts = newLoopVerts
            
    return loopVerts #array of vertex index arrays



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



def gethairTemplateType(obj, sepObj):
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
        MG_attrs = activeSys.settings.MG_attrs
        
        activeSysData = bpy.data.particles[partSys[partSys.active_index].settings.name]
        try:
            sepObj = separateObj(MG_attrs.hairTemplate)
            formType = gethairTemplateType(MG_attrs.hairTemplate, sepObj)
            loops = getLoops(MG_attrs.hairTemplate, sepObj, formType)
            
            for ob in loops:
                for i in range(len(ob)-1):
                    length = len(ob[i])
                    length2 = len(ob[i+1])
                    if length != length2:
                        self.report({'ERROR'}, 'all sides of hairTemplate must have the same length')
            
        except AttributeError:
            self.report({'ERROR'}, "Hair form must be mesh object with seams marked where the hair roots start")
            
            
        bpy.ops.particle.edited_clear()
        
        guidesN = 0
        guideSeg = len(loops[0][0])
        for i in range(len(formType)):
            if MG_attrs.stripTube or (formType[i] == FormType.CARD) or (formType[i] == FormType.SPIKE):
                guidesN = guidesN + len(loops[i]) + ((len(loops[i])-1) * MG_attrs.stripSubdiv) + \
                          (MG_attrs.stripTube and ((formType[i] == FormType.TUBE) or (formType[i] == FormType.CONE))) * \
                          MG_attrs.stripSubdiv
            if (formType[i] == FormType.TUBE) or (formType[i] == FormType.CONE):
                guidesN = guidesN + MG_attrs.guideCount
            
        activeSysData.count = guidesN
        activeSysData.hair_step = guideSeg - 1
        activeSysData.display_step = 6
            
        bpy.ops.particle.particle_edit_toggle()
        bpy.context.scene.tool_settings.particle_edit.tool = 'COMB'
        contextOveride = AssembleOverrideContextForView3dOps()
        bpy.ops.particle.brush_edit(contextOveride, stroke=[{'name':'',
                                                             'location':(0,0,0),
                                                             'mouse':(0,0),
                                                             'pressure':0,
                                                             'size':0,
                                                             'pen_flip':False,
                                                             'time':0,
                                                             'is_start':False}])
        bpy.ops.particle.particle_edit_toggle()
        
        context.scene.tool_settings.particle_edit.use_emitter_deflect = False
        context.scene.tool_settings.particle_edit.use_preserve_root = False
        context.scene.tool_settings.particle_edit.use_preserve_length = False
            
        depsgraph = context.evaluated_depsgraph_get()
        depObj = context.object.evaluated_get(depsgraph)
        depPSys = depObj.particle_systems[partSys.active_index]
        
        shift = 0
        for i in range(len(formType)):
            if MG_attrs.stripTube or (formType[i] == FormType.CARD) or (formType[i] == FormType.SPIKE):
                for loop in range(len(loops[i])):
                    part = depPSys.particles[loop + shift]  
                    part.location = MG_attrs.hairTemplate.data.vertices[loops[i][loop][0]].co
                    for vert in range(len(loops[i][loop])):
                        part.hair_keys[vert].co = MG_attrs.hairTemplate.data.vertices[loops[i][loop][vert]].co
                
                loopsMap = [j for j in range(len(loops[i]))]
                if (formType[i] == FormType.CONE) or (formType[i] == FormType.TUBE):
                    loopsMap.append(loopsMap[0])
                     
                for loop in loopsMap[:-1]:
                    for j in range(MG_attrs.stripSubdiv):
                        part = depPSys.particles[shift + len(loops[i]) + loop*MG_attrs.stripSubdiv + j]

                        for vert in range(len(loops[i][loop])):
                            co = (MG_attrs.hairTemplate.data.vertices[loops[i][loop][vert]].co * (j + 1) + \
                                  MG_attrs.hairTemplate.data.vertices[loops[i][loopsMap[loop+1]][vert]].co * \
                                 (MG_attrs.stripSubdiv - j)) / (MG_attrs.stripSubdiv + 1)
                                 
                            if vert == 0:
                                part.location = co

                            part.hair_keys[vert].co = co
                            
                
                shift = shift + len(loops[i]) + (len(loopsMap)-1) * MG_attrs.stripSubdiv
                
            if ((formType[i] == FormType.TUBE) or (formType[i] == FormType.CONE)) and (MG_attrs.guideCount > 0) and ((MG_attrs.dist == 'normal') or (MG_attrs.dist == 'const')):
                part = depPSys.particles[shift]
                
                #generate center hair
                centerHair = []
                for vert in range(len(loops[i][0])):
                    x, y, z = [], [], []
                    l = len(loops[i])
                    for loop in range(len(loops[i])):
                        co = MG_attrs.hairTemplate.data.vertices[loops[i][loop][vert]].co
                        x.append(co.x)
                        y.append(co.y)
                        z.append(co.z)
                        
                    newPoint = Vector((sum(x)/l, sum(y)/l, sum(z)/l))
                    if vert == 0:
                        part.location = newPoint
                        
                    centerHair.append(newPoint)
                    part.hair_keys[vert].co = newPoint
                
                #generate interpolated hair
                if MG_attrs.dist == 'normal':
                    random.seed(MG_attrs.distSeed)
                    for j in range(1, MG_attrs.guideCount):
                        part = depPSys.particles[shift + j]
                        distMaxWidth = 11 - MG_attrs.distWidth
                        distWidth = 11 - MG_attrs.distSharpness
                        
                        if distWidth < distMaxWidth:
                            raise Exception("Width must be equal to or less than Max Width")
                            
                        
                        refCount = random.randint(distMaxWidth, distWidth)
                        refLoops = []
                        for k in range(refCount):
                            refLoops.append(random.randint(0, len(loops[i])-1))
                            
                        for vert in range(len(loops[i][0])):
                            x, y, z = [], [], []
                            l = refCount
                            for k in refLoops:
                                  co = MG_attrs.hairTemplate.data.vertices[loops[i][k][vert]].co
                                  x.append(co.x)
                                  y.append(co.y)
                                  z.append(co.z)
                                  
                            newPoint = Vector(((sum(x)/l),
                                               (sum(y)/l),
                                               (sum(z)/l)))
                            if vert == 0:
                                part.location = newPoint
                            
                            part.hair_keys[vert].co = newPoint
                            
                elif MG_attrs.dist == 'const':
                    random.seed(MG_attrs.jitterSeed)
                    minHairPerDiv = int((MG_attrs.guideCount-1) / len(loops[i]))
                    extraHairs = (MG_attrs.guideCount-1) % len(loops[i])
                    
                    localShift = 1
                    
                    sortLoopMap = [[j for j in range(floor(len(loops[i])/2))]]
                    while len(sortLoopMap[-1]) > 3:
                        tempLoopMap = []
                        for j in sortLoopMap:
                            tempLoopMap.append(j[:-floor(len(j)/2)])
                            tempLoopMap.append(j[floor((len(j)+1)/2):])
                        sortLoopMap = tempLoopMap
                        
                    while len(sortLoopMap[0]) < floor(len(loops[i])/2):
                        tempLoopMap = []
                        for j in range(floor(len(sortLoopMap)/2)):
                            tempLoopMap.append([])
                            for k in range(len(sortLoopMap[j*2])):
                                tempLoopMap[-1].append(sortLoopMap[j*2][k])
                                if  k < len(sortLoopMap[j*2+1]): 
                                    tempLoopMap[-1].append(sortLoopMap[j*2+1][k])
                        sortLoopMap = tempLoopMap
                    
                    sortLoopMap = sortLoopMap[0]
                    tempLoopMap = []
                    for j in range(len(sortLoopMap)):
                        tempLoopMap.append(sortLoopMap[j])
                        tempLoopMap.append(sortLoopMap[j] + floor(len(loops[i])/2))
                    sortLoopMap = tempLoopMap
                        
                    if len(loops[i]) % 2:
                        sortLoopMap.append(len(loops[i])-1)
                        
                    for j in range(0, len(loops[i])):
                        extra = 0
                        if j < extraHairs:
                            extra = 1
                        for k in range(minHairPerDiv + extra):
                            part = depPSys.particles[shift + localShift]
                            localShift = localShift + 1
                            
                            randX, randY, randZ = (random.random()-.5)*2, (random.random()-.5)*2, (random.random()-.5)*2 
                            for vert in range(len(loops[i][0])):
                                co = MG_attrs.hairTemplate.data.vertices[
                                                    loops[i][sortLoopMap[j]][vert]
                                                    ].co
                                
                                distVector = co - centerHair[vert]
                                randScale = sqrt(distVector.x**2 + distVector.y**2 + distVector.z**2)
                                jitter = MG_attrs.jitter * randScale
                                
                                co = co * (k + 1)
                                center = centerHair[vert] * (minHairPerDiv + extra - k)
                                newPoint = Vector((sum([co.x, center.x])/(minHairPerDiv+extra+1) + (randX*jitter),
                                                   sum([co.y, center.y])/(minHairPerDiv+extra+1) + (randY*jitter),
                                                   sum([co.z, center.z])/(minHairPerDiv+extra+1) + (randZ*jitter)))
                                                   
                                if vert == 0:
                                    part.location = newPoint
                                    
                                part.hair_keys[vert].co = newPoint
                                
                shift = shift + MG_attrs.guideCount
                                
            elif (MG_attrs.dist == 'complex') and ((formType[i] == FormType.TUBE) or (formType[i] == FormType.CONE)):
                ptPositions = []
                ptWeights = []
                xyPolygons = []
                for j in range(len(loops[i][0])): #loop through vertex layers
                    
                    def getPlaneNormal():
                        planeVectors = []
                        for k in range(3):
                            x, y, z = [], [], []
                            l = len(loops[i])
                            for loop in range(len(loops[i])): #loop through loops
                                co = MG_attrs.hairTemplate.data.vertices[loops[i][loop][j]].co
                                x.append(co.x)
                                y.append(co.y)
                                z.append(co.z)
                                
                            center = Vector((sum(x)/l, sum(y)/l, sum(z)/l))
                            
                            # Set x,y,z values in reference to the center of mass for the given ring on the hair form mesh
                            x = [k-center.x for k in x]
                            y = [k-center.y for k in y]
                            z = [k-center.z for k in z]
                            
                            if k == 0:
                                temp = z
                                z = x
                                x = temp
                            if k == 1:
                                temp = z
                                z = y
                                y = temp
                            
                            # Equation for fitting a plane to data points
                            # https://www.ilikebigbits.com/2015_03_04_plane_from_points.html
                            planeMatrix = np.matrix([x, y, z])
                            planeZ = np.matrix(z).getT() * -1
                            cross = (planeMatrix.dot(planeMatrix.getT()))[:2,:2]
                            crossZ = (planeMatrix.dot(planeZ))[:2]
                            D = cross[0,0]*cross[1,1] - cross[0,1]*cross[1,0]
                            a = crossZ[0,0]*cross[1,1] - cross[0,1]*crossZ[1,0]
                            b = cross[0,0]*crossZ[1,0] - crossZ[0,0]*cross[1,0]
                            
                            if k == 0:
                                planeVectors.append( (D,b,a) )
                            elif k == 1:
                                planeVectors.append( (a,D,b) )
                            else:
                                planeVectors.append( (a,b,D) )
                             
                        index = 0
                        for k in range(1,3):
                            if planeVectors[k][k] > planeVectors[index][index]:
                                index = k
                        
                        return (Vector(planeVectors[k]).normalized(), center)
                    
                    normal, center = getPlaneNormal()
                    
                    def moveToPlane(n, cpt, pt):
                        #find if vector between point and new point on plane (Vp-p) is parallel with plane normal (N)
                        #by taking cross product of vector Vp-p and normal N such that
                        #               Vp-p X N = (0,0,0)
                        #find if vector between plane center and new point on plane (Vc-p) is orthogonal to normal
                        #by taking dot product of vectr Vc-p and normal N such that
                        #               Vc-p . N = 0
                        pt = pt - cpt #set the point being moved to plane in coordinates shifted to plane center
                        
                        if n.y == max(n):
                            ptOnPlaneY = (-pt.x*n.x*n.y + pt.y*n.x**2 + pt.y*n.z**2 - pt.z*n.z*n.y)\
                                         /(n.x**2 + n.y**2 + n.z**2)
                            
                            ptOnPlaneZ = (-pt.y*n.z + pt.z*n.y + ptOnPlaneY*n.z)\
                                         /n.y
                                         
                            ptOnPlaneX = (-pt.x*n.y + pt.y*n.x + ptOnPlaneY*n.x)\
                                         /n.y
                        elif n.z == max(n):
                            ptOnPlaneZ = (-pt.x*n.x*n.z + pt.z*n.x**2 + pt.z*n.y**2 - pt.y*n.y*n.z)\
                                         /(n.x**2 + n.y**2 + n.z**2)
                            
                            ptOnPlaneX = (-pt.z*n.x + pt.x*n.z + ptOnPlaneZ*n.x)\
                                         /n.z
                                         
                            ptOnPlaneY = (-pt.z*n.y + pt.y*n.z + ptOnPlaneZ*n.y)\
                                         /n.z
                                         
                        else:
                            ptOnPlaneX = (-pt.z*n.z*n.x + pt.x*n.y**2 + pt.x*n.z**2 - pt.y*n.y*n.x)\
                                         /(n.x**2 + n.y**2 + n.z**2)
                            
                            ptOnPlaneY = (-pt.x*n.y + pt.y*n.x + ptOnPlaneX*n.y)\
                                         /n.x
                                         
                            ptOnPlaneZ = (-pt.x*n.z + pt.z*n.x + ptOnPlaneX*n.z)\
                                         /n.x

                        return Vector((ptOnPlaneX, ptOnPlaneY, ptOnPlaneZ))
                    
                    
                    polygon = [] #create a flat polygon out of the given layer of the hair form mesh
                    for loop in range(len(loops[i])): #loop through loops
                            co = MG_attrs.hairTemplate.data.vertices[loops[i][loop][j]].co
                            coOnPlane = moveToPlane(normal, center, co)
                            polygon.append(coOnPlane)
                            
                    def rotateToXY(n, pt): #assumes pt is already in reference to the plane center
                        #Gets the Y-axis angle between the planar normal and the z axis unit vector (0,0,1) 
                        #Rotates the given point pt, and the planar normal on the y axis the calculated angle
                        #Gets the X-axis angle between the now rotated planar normal and the z axis unit vector
                        #Rotates the given point pt on the x axis the calculated angle.
                        #The point pt should now have a Z value of zero because its plane was rotated to the (X,Y) plane
                        
                        #zaxis angle
                        try:
                            zAxisTheta = acos(n.x/(sqrt(n.y**2+n.x**2)*sqrt(1**2)))
                        except ZeroDivisionError:
                            zAxisTheta = 0
                        if n.y > 0:
                            zAxisTheta = -zAxisTheta
                            
                        xPrime = pt.x*cos(zAxisTheta) - pt.y*sin(zAxisTheta)
                        yPrime = pt.x*sin(zAxisTheta) + pt.y*cos(zAxisTheta)
                        
                        n_xPrime = n.x*cos(zAxisTheta) - n.y*sin(zAxisTheta)
                        
                        try:
                            yAxisTheta = acos(n.z/(sqrt(n_xPrime**2+n.z**2)*sqrt(1**2+0)))
                        except ZeroDivisionError:
                            yAxisTheta = 0
                        if n.x < 0:
                            yAxisTheta = -yAxisTheta
                        
                        #rotate on y axis:
                        xPrimePrime = xPrime*cos(yAxisTheta) - pt.z*sin(yAxisTheta)
                        zPrime = xPrime*sin(yAxisTheta) + pt.z*cos(yAxisTheta)
                        return Vector((xPrimePrime, yPrime, zPrime))
                    
                    xyPolygon = []
                    for v in polygon:
                        xyPolygon.append(rotateToXY(normal, v))
                        
                    xyPolygons.append(xyPolygon)
                    
                    def rotateToVector(ref, pt):
                        ref = ref.normalized()

                        yAxisTheta = -(pi/2 - asin(ref.z))
                        
                        #rotate on y axis:
                        xPrime = pt.x*cos(yAxisTheta) - pt.z*sin(yAxisTheta)
                        zPrime = pt.x*sin(yAxisTheta) + pt.z*cos(yAxisTheta)
                        
                        try:
                            zAxisTheta = acos(ref.x/(sqrt(ref.y**2+ref.x**2)*sqrt(1**2)))
                        except ZeroDivisionError:
                            zAxisTheta = 0
                        if ref.y < 0:
                            zAxisTheta = -zAxisTheta
                        
                        #rotate on z axis:
                        xPrimePrime = xPrime*cos(zAxisTheta) - pt.y*sin(zAxisTheta)
                        yPrime = xPrime*sin(zAxisTheta) + pt.y*cos(zAxisTheta)
                        
                        return Vector((xPrimePrime, yPrime, zPrime))
                        
                    
#                    def angle2d(v1, v2, center):
#                        #angle between the vectors v1-center and v2-center
#                        v1 = v1 - center
#                        v2 = v2 - center
#                        
#                        try:
#                            zAxisTheta = acos((v1.x*v2.x + v1.y*v2.y)\
#                            /(sqrt(v1.x**2+v1.y**2)*sqrt(v2.x**2+v2.y**2)))
#                        except ZeroDivisionError:
#                            zAxisTheta = 0
#                            
#                        return zAxisTheta
                    
#                    def sameAngleSide(v1, v2, v3, v4):
#                        # for a 4-vertex line, check if first angle is on the same side
#                        # of the center line as the second angle. This will determine if
#                        # pi needs to be added to the second angle or not
#                        #        v1 \___/ v4          v1 \___ v3
#                        #          v2  v3               v2   \ v4
#                        
#                        if (v2.x-v3.x) == 0:
#                            v1Side = (v1.x-v2.x) >= 0
#                            v4Side = (v4.x-v2.x) >= 0
#                        
#                        v1Side = (v2.y-v3.y)/(v2.x-v3.x)*v1.x - v1.y + v2.y - \
#                                 (v2.y-v3.y)/(v2.x-v3.x)*v2.x >= 0
#                        v4Side = (v2.y-v3.y)/(v2.x-v3.x)*v4.x - v4.y + v2.y - \
#                                 (v2.y-v3.y)/(v2.x-v3.x)*v2.x >= 0
#                        return (v1Side == v4Side)
#                       
#                    def insidePolyVector(v): 
#                        angles = [angle2d(xyPolygon[0], xyPolygon[-2], xyPolygon[-1])]
#                        #the inside/outside reference is the acute angle on the first section
#                        flip = 0
#                        for k in range(1, len(xyPolygon)):
#                            angles.append(angle2d(xyPolygon[k], xyPolygon[k-2], xyPolygon[k-1]))
#                            line = xyPolygon[k-1] - xyPolygon[k-2]
#                            sameSide = sameAngleSide(xyPolygon[k-3],
#                                                     xyPolygon[k-2],
#                                                     xyPolygon[k-1],
#                                                     xyPolygon[k]
#                                                     )
#                            if (sameSide and flip) or (not sameSide and not flip):
#                                angles[-1] = 2*pi - angles[-1]
#                                flip = 1
#                            else:
#                                flip = 0
#                        
#                        #print(sum(angles), pi*(len(loops[i])-2), sum([(2*pi - a) for a in angles]))
                    
#                    def rotateVector(v, p, theta):
#                        #rotate vector v around pivot p theta radians
#                        # +theta = counterclock wise, -theta = clockwise
#                        vp = v-p
#                        
#                        xPrime = vp.x*cos(theta) - vp.y*sin(theta)
#                        yPrime = vp.x*sin(theta) + vp.y*cos(theta)
#                        
#                        v = Vector((xPrime+p.x, yPrime+p.y, v.z))
#                        
#                        return v
                    
                    def insidePoly(pt):
                        #https://www.geeksforgeeks.org/how-to-check-if-a-given-point-lies-inside-a-polygon/
                        inf = Vector((int(1e10), pt.y, 0))
                        
                        def getOrientation(p, q, r):
                            orientation = (q.y-p.y)*(r.x-q.x) - (q.x-p.x)*(r.y-q.y)
                            if orientation == 0:
                                return 0 #colinear
                            return 1 if (orientation > 0) else 2 #clock or counterclock wise
                        
                        def onSegment(p, q, r):
                            if (q.x <= max(p.x, r.x)) and (q.x >= min(p.x, r.x)) \
                            and (q.y <= max(p.y, r.y)) and (q.y >= min(p.y, r.y)):
                                return True
                            return False
                        
                        def doIntersect(p1, q1, p2, q2):
                            o1 = getOrientation(p1, q1, p2)
                            o2 = getOrientation(p1, q1, q2)
                            o3 = getOrientation(p2, q2, p1)
                            o4 = getOrientation(p2, q2, q1)
                            
                            if (o1 != o2) and (o3 != o4):
                                return True
                            
                            if o1 == 0 and onSegment(p1, p2, q1):
                                return True
                            if o2 == 0 and onSegment(p1, q2, q1):
                                return True
                            if o3 == 0 and onSegment(p2, p1, q2):
                                return True
                            if o4 == 0 and onSegment(p2, q1, q2):
                                return True
                            
                            return False
                        
                        count = 0
                        for k in range(len(xyPolygon)):
                            if doIntersect(xyPolygon[k-1], xyPolygon[k], pt, inf):
                                if getOrientation(polygon[k-1], pt, polygon[k]) == 0:
                                    return onSegment(polygon[k-1], pt, polygon[k])
                                
                                count = count + 1
                        return count%2 == 1
                        
                    minX = min([k.x for k in xyPolygon])
                    minY = min([k.y for k in xyPolygon])
                    maxX = max([k.x for k in xyPolygon])
                    maxY = max([k.y for k in xyPolygon])
                    
                    
                    
                    if j == 0:
                        #randomly generate guideCount number of points on first layer
                        l = 0
                        while len(ptPositions) <  MG_attrs.guideCount and l < 100:
                            l = 1 + 1
                            randX = random.uniform(minX, maxX)
                            randY = random.uniform(minY, maxY)
                            
                            point = Vector((randX, randY, 0))
                            inside = insidePoly(point)
                            if inside:
                                ptPositions.append(point)
                                
                    else:
                        #transform last layers points with changes between this and last layer poly
                        newPtPositions = []
                        for k in range(len(ptPositions)):
                            weightedDist = Vector((0,0,0))
                            for l in range( len(xyPolygon) ):
                                dist = xyPolygon[l] - xyPolygons[j-1][l]
                                weightedDist = weightedDist + (dist * ptWeights[k][l])
                                
                            point = weightedDist + ptPositions[k]
                            newPtPositions.append( point )
                            
                        ptPositions = newPtPositions
                                
                    #move the particles to the positions found in ptPositions
                    for k in range(MG_attrs.guideCount): #loop though hairGuides
                        part = depPSys.particles[shift + k]
                        part.hair_keys[j].co = rotateToVector(normal, ptPositions[k]) + center
                        
                        if j == 0:
                            part.location = ptPositions[k]
                    
                    #generate new weights for the current polygon
                    
                    for k in ptPositions:
                        weight = []
                        weightNumerator = []
                        for l in xyPolygon:
                            dist = k-l
                            if dist.x == 0 and dist.y == 0:
                                weightNumerator.append( 1e10 )
                            else:
                                weightNumerator.append( 1/(sqrt(dist.x**2 + dist.y**2)**2) )
                                
                        for l in weightNumerator:
                            weight.append( l / sum(weightNumerator) )
                        ptWeights.append(weight)
                            
                
                shift = shift + MG_attrs.guideCount        
                
        bpy.ops.particle.particle_edit_toggle()
        bpy.ops.particle.particle_edit_toggle()
        return {'FINISHED'}



#-----------------------------------------------------------------------
#          GUI Panel in ParticleSettings Properties Menu
#-----------------------------------------------------------------------
#GUI panel for addon found in properties -> particles (that's set to hair)
class ManeGenPanel(Panel):
    """Creates a panel in the Particles properties window"""
    
    bl_label = "ManeGen"
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
        
        col = layout.column()
        
        MG_attrs = partSys[partSys.active_index].settings.MG_attrs
        
        row = col.split(factor = .5, align=True)
        row.alignment = 'RIGHT'
        row.label(text = 'Hair Template')
        row.prop(MG_attrs, "hairTemplate", text='')
        
        box = col.box()
        
        row = box.row()
        row.alignment = 'CENTER'
        row.label(text = 'Volume:')
        
        row = box.row()
        row.alignment = 'LEFT'
        row.label(text = 'Hair Interpolation:')
        
        row = box.split(factor = .5, align=True)
        row.alignment = 'RIGHT'
        row.label(text = "Guide Count")
        row.prop(MG_attrs, "guideCount", text = '')
        #if MG_attrs.followMesh:
        #    row.enabled = False
        #else:
        #    row.enabled = True
            
        box.row().separator()
        
        row = box.row()
        row.alignment = 'LEFT'
        row.label(text = 'Hair Distribution:')
        
        row = box.row(align = True)
        row.alignment = 'RIGHT'
        row.label(text = 'Distribution')
        row.prop(MG_attrs, 'dist', text = '')
        
        if MG_attrs.dist == 'normal':            
            row = box.split(factor = .5, align=True)
            row.alignment = 'RIGHT'
            row.label(text = 'Avg Width')
            row.prop(MG_attrs, 'distSharpness', text = '')
                
            row = box.split(factor = .5, align=True)
            row.alignment = 'RIGHT'
            row.label(text = 'Outer Width')
            row.prop(MG_attrs, 'distWidth', text = '')
            
            if MG_attrs.distWidth < MG_attrs.distSharpness:
                row = box.row()
                row.alignment = 'RIGHT'
                row.label(text = 'Avg Width > Max Width', icon = "ERROR")
                
            row = box.split(factor = .5, align=True)
            row.alignment = 'RIGHT'
            row.label(text = 'Distribution Seed')
            row.prop(MG_attrs, 'distSeed', text = '')
                
        elif MG_attrs.dist == 'const':
            row = box.split(factor = .5, align=True)
            row.alignment = 'RIGHT'
            row.label(text = 'Jitter')
            row.prop(MG_attrs, 'jitter', text = '')
            
            row = box.split(factor = .5, align=True)
            row.alignment = 'RIGHT'
            row.label(text = 'Jitter Seed')
            row.prop(MG_attrs, 'jitterSeed', text = '')
        
        
        box = col.box()
        
        row = box.row()
        row.alignment = 'CENTER'
        row.label(text = 'Edge:')
        
        row = box.split(factor = .5, align=True)
        row.alignment = 'RIGHT'
        row.label(text = 'Subdiv')
        row.prop(MG_attrs, "stripSubdiv", text = '')
        
        row = box.row(align = True)
        row.alignment = 'RIGHT'
        row.label(text = 'Use edge guides on volume objects')
        row.prop(MG_attrs, 'stripTube', text = '')
        
        row = col.row()
        row.operator("particle.hair_style")



#-----------------------------------------------------------------------
#                    Hair System variables
#-----------------------------------------------------------------------
class PartSettingsProperties(PropertyGroup):
    options = [
            ('normal', 'Avg Gaussian', '', '', 0),
            ('const', 'Avg Const', '', '', 1),
            ('complex', 'Complex Vector', '', '', 2),
            ]
    
    hairTemplate: PointerProperty(
        type = Object
        )
    guideCount: IntProperty(
        default = 0,
        min = 0)
    distSeed: IntProperty(
        default = 0,
        min = -2147483647,
        max = 2147483647)
    stripSubdiv: IntProperty(
        default = 0,
        min = 0,
        max = 20)
    stripTube: BoolProperty(
        default = False)
    distWidth: IntProperty(
        default = 1,
        min = 1,
        max = 10)
    distSharpness: IntProperty(
        default = 2,
        min = 1,
        max = 10)
    jitterSeed: IntProperty(
        default = 0,
        min = -2147483647,
        max = 2147483647)
    jitter: FloatProperty(
        min = 0,
        step = 1)
    dist: EnumProperty(
        items = options
        )



#-----------------------------------------------------------------------
#                         Registration
#-----------------------------------------------------------------------
classes = (
    PartSettingsProperties,
    GrowHair,
    ManeGenPanel,
)



def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.ParticleSettings.MG_attrs = PointerProperty(type=PartSettingsProperties)
    
def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.ParticleSettings.MG_attrs

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