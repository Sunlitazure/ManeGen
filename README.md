# ManeGen
Generate hair from mesh

### Example!
The tips of the hair were brushed into clumps, and the roots extended down in 'Particle Edit' mode after being generated. Those are the only modifications made after generation.

<img src="/readme_images/addon_hair_render.PNG" width="50%">
<img src="/readme_images/addon_hair_render_wTemp.PNG">
<img src="/readme_images/addon_hair_render_tempOnly.PNG">

## Use

Once ManeGen.py is installed and enabled in properties it will be found in the particles panel once a particle system has been created and set to Hair.

<img src="/readme_images/addon_prop_panel.PNG">

### Behavior
ManeGen behaves similarly to Jandals' HairNet, but is more tailored to creating hair styles for characters (I think. Maybe I'm just using it wrong.)

For types of hair template shapes are supported. Tube like objects, tubes terminating with a single vertex, planes, and planes terminating with a single vertex. 

The mesh used as the hair template must have the edge at the hair roots set as a seam. See the image below

_Every_ edge perpendicular to the seam must be the same length for _every_ mesh in the object for it to work properly.

<img src="/readme_images/addon_hair_form.PNG" width="60%">

The hair template object can have as many separate meshes and be as complex as you wish, so long as each mesh in the object follows the above stated rules.

Any time changes are made to the ManeGen settings the hair will need to be generated using the 'Style Hair' button again.

All changes made to the hair in 'Hair Edit' mode will be lost when clicking the 'Style Hair' button. Doing so completely resets the hair edit and regenerates the hair.

### Generate Hair

In the ManeGen panel, choose the hair template object in the 'Hair Template' box. Hair template object must be a mesh object and must follow the rules stated in the section above.

Once your settings are how you want them, click the 'Style Hair' button to generate the hairs. You must be in object mode in the 3d viewport for the button to be available.

Hair generation will ignore the settings in the 'Emission' panel because those values are defined either in the ManeGen panel or template object itself.

Depending on how many vertices the hair template object has and the guide count, it may take a few minutes to finish generating the hair.

Once you are happy with how the hair is generated I suggest enabling 'Lock Hair Generation' so you never accidentally reset the hair style. Then use 'Hair Edit' mode to make any minor adjustments you wish to make the hair look perfect.

<img src="/readme_images/addon_hair_form_wHair.PNG" width="60%">
<img src="/readme_images/addon_hair_form_wHairEdit.PNG" width="60%">

### Settings

- **Hair Template:** The mesh object used as the template to generate the hair

#### - Volume sub-panel
This defines settings for volumetric hair generation, i.e. _tube-like_ template objects

- **Guide Count:** How many parent hairs to create

- **Distribution:** Algorithm for generating the volumetric hair. You should almost always use the **Complex Vector** algorithm. The other two are far more simple and will likely give much worse results. You're free to experiment with them to see what they do if you wish

- **Template Sub Div:** Small values will cause generated hairs to congregate near vertices. Higher values will create a more uniform distribution but may take longer to generate hair. It performs a simple subdivision on the cross sectional areas of the hair template object so there are more vertices to sample from when placing hairs (does not make any changes to the template object)

- **Distribution Seed:** Random number generator seed. Changes the random pattern used to place the hairs

- **Z Randomize Size:** How much each hair can be placed higher/lower than other hairs. Used to feather the hair ends for a more natural appearance

#### - Edge sub-panel
This defines settings for direct hair guide generation, i.e. _planar_ template objects

### Limitations
- The hairs get moved around, so when applying a texture map to the hair, UVs can't be used. Try using the 'Generated' or 'Object' options in the 'Texture Coordinate' node instead. See the hair_texture_example.blend example

- Every edge perpendicular to the seam must be the same length for every mesh in the template object. This is because every hair in the hair system has to have the same number of segments

- The mesh template must have at least two segments for each hair guide path to work

- Using the 'Complex Vector' algorithm, the cross sections are approximated as flat planes. So if your cross sections are too non-planar the generated hair may not stay inside the template mesh very well.
