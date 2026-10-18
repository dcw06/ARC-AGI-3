"""Named, frozen instructions; the legacy prompt remains byte-identical."""

LEGACY_PROFILE = 'legacy_whole_v1'
DETAILED_PROFILE = 'detailed_whole_v2'

DETAILED_PROMPT = """Examine this pixel-based game image and point to every distinct visible whole object. Discover the object inventory from the image itself. There is no predetermined object count.

Use the following rules consistently:

1. Identify complete visual entities.
   Include distinct pieces, markers, symbols, bounded structural features, patterned assemblies, and separate interface elements that are visibly present. Include small, thin, plain, and partially visible objects as well as large or visually prominent ones. An object does not need to resemble a familiar real-world item or have an obvious purpose.
2. Determine object identity from visual organization.
   Consider outlines, boundaries, enclosure, alignment, repeated structure, and relationships between neighboring regions. A single object can contain several colors, a border, an internal symbol, holes, or multiple disconnected pieces. Do not automatically split it at every color change or gap. Conversely, touching regions or regions of the same color can belong to different objects.
3. Preserve separate instances.
   When several complete objects share the same appearance, point to each instance separately. Similar color, shape, size, or alignment alone is insufficient to merge them. Group several elements into one object only when their arrangement provides clear evidence of a coherent whole.
4. Keep whole objects and internal parts distinct.
   For a composite object, identify the complete assembly once. Do not also point to its border, decoration, individual colored cells, and other internal components as additional whole objects. However, spatial containment alone does not make something an internal part: a distinct piece or marker placed within a larger area can remain a separate object. Use the same distinction throughout the image.
5. Distinguish objects from their surroundings.
   Do not count empty space, an undifferentiated background, or incidental pixel boundaries as objects. Do not assume a particular color always means background, wall, or empty space. Include a bounded region or interface element when its visible structure distinguishes it as an entity; do not exclude it merely because it is stationary or outside the main arrangement of pieces.
6. Use visible evidence without inventing game rules.
   Identify what is present without assuming which object is controllable, movable, dangerous, collectible, a destination, or a button. Those functions require separate evidence. Do not invent hidden objects or additional instances to complete an expected pattern.
7. Place one point on each identified object.
   Choose a visible location belonging to the object itself, preferably within a clearly distinguishable region and away from an ambiguous boundary. For hollow, concave, or disconnected objects, choose an occupied visible portion rather than an empty geometric center. Each point must identify one object, and each object must receive only one point.
8. Return only the pointing result.
   Use the native pointing format. Do not add descriptions, explanations, a written count, coordinate tables, or JSON. Check the entire image for missed objects and duplicate detections before finishing. End normally after the final point; do not repeat the inventory or continue counting."""


def select_prompt(profile, legacy_prompt):
    if profile == LEGACY_PROFILE:
        return legacy_prompt
    if profile == DETAILED_PROFILE:
        return DETAILED_PROMPT
    raise ValueError('unknown frozen object-discovery prompt profile')
