"""Deterministic lossless grid rendering and pinned-processor resize arithmetic (stdlib only)."""
import base64,hashlib,math,struct,zlib

# Renderer palette for this preflight: 16 distinct RGB triples. It is this
# package's documented legend, sent to the model as text; not a claim about any
# official game palette.
PALETTE=[(255,255,255),(204,204,204),(153,153,153),(102,102,102),(51,51,51),(0,0,0),
    (229,58,163),(255,123,204),(249,60,49),(30,147,255),(136,216,241),(255,220,0),
    (255,133,27),(146,18,49),(79,204,48),(163,86,214)]
CELL=16
# Pinned preprocessor_config.json at the frozen revision (see protocol).
PATCH,MERGE,MIN_PIXELS,MAX_PIXELS=16,2,65536,16777216

def check_grid(grid):
    if (type(grid) is not list or not 1<=len(grid)<=64 or type(grid[0]) is not list or not 1<=len(grid[0])<=64
        or any(type(r) is not list or len(r)!=len(grid[0]) or any(type(v) is not int or not 0<=v<=15 for v in r) for r in grid)):
        raise ValueError('grid')

def png(grid,cell=CELL):
    """Each cell is a uniform cell x cell block; RGB, 8-bit, no filtering, fixed zlib level."""
    check_grid(grid)
    rows=bytearray()
    for r in grid:
        line=b''.join(bytes(PALETTE[v])*cell for v in r)
        for _ in range(cell):rows+=b'\x00'+line
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    header=struct.pack('!IIBBBBB',len(grid[0])*cell,len(grid)*cell,8,2,0,0,0)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',header)+chunk(b'IDAT',zlib.compress(bytes(rows),9))+chunk(b'IEND',b'')

def decode(raw):
    """Independent PNG reader for the exact encoding above; returns the grid of palette indices."""
    if raw[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('png signature')
    pos=8;data=b'';width=height=None
    while pos<len(raw):
        size=struct.unpack('!I',raw[pos:pos+4])[0];kind=raw[pos+4:pos+8];body=raw[pos+8:pos+8+size]
        if zlib.crc32(kind+body)&0xffffffff!=struct.unpack('!I',raw[pos+8+size:pos+12+size])[0]:raise ValueError('png crc')
        if kind==b'IHDR':
            width,height,depth,color,_,_,_=struct.unpack('!IIBBBBB',body)
            if (depth,color)!=(8,2):raise ValueError('png format')
        elif kind==b'IDAT':data+=body
        pos+=12+size
    pixels=zlib.decompress(data);stride=width*3+1;index={rgb:i for i,rgb in enumerate(PALETTE)}
    image=[]
    for y in range(height):
        row=pixels[y*stride:(y+1)*stride]
        if row[0]!=0:raise ValueError('png filter')
        image.append([index[tuple(row[1+3*x:4+3*x])] for x in range(width)])
    return width,height,image

def grid_from_png(raw,cell=CELL):
    width,height,image=decode(raw)
    if width%cell or height%cell:raise ValueError('cell alignment')
    grid=[[image[y*cell][x*cell] for x in range(width//cell)] for y in range(height//cell)]
    for y in range(height):
        for x in range(width):
            if image[y][x]!=grid[y//cell][x//cell]:raise ValueError('non-uniform cell')
    return grid

def data_url(raw):return 'data:image/png;base64,'+base64.b64encode(raw).decode()

def smart_resize(height,width,factor=PATCH*MERGE,min_pixels=MIN_PIXELS,max_pixels=MAX_PIXELS):
    """Provisional arithmetic mirroring the Qwen2-VL resize rule; verified on target, never assumed."""
    h=round(height/factor)*factor;w=round(width/factor)*factor
    if h*w>max_pixels:
        beta=math.sqrt(height*width/max_pixels);h=math.floor(height/beta/factor)*factor;w=math.floor(width/beta/factor)*factor
    elif h*w<min_pixels:
        beta=math.sqrt(min_pixels/(height*width));h=math.ceil(height*beta/factor)*factor;w=math.ceil(width*beta/factor)*factor
    return h,w

def expected_image_tokens(height,width):
    h,w=smart_resize(height,width)
    return {'processed_height':h,'processed_width':w,'grid_thw':[1,h//PATCH,w//PATCH],'image_tokens':(h//PATCH)*(w//PATCH)//(MERGE*MERGE)}

def sha(raw):return hashlib.sha256(raw).hexdigest()
