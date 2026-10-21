"""Continuous curves reconstructed from the design's axis, diamonds and S feathers."""
import numpy as np


def bezier(control, count=65):
    control = np.asarray(control, dtype=float)
    t = np.linspace(0, 1, count)[:, None]
    return (1-t)**3*control[0] + 3*(1-t)**2*t*control[1] + 3*(1-t)*t*t*control[2] + t**3*control[3]


def build_stitches(spec):
    rows = []
    scale = spec['trace']['world_width']/2
    loft = spec['trace']['thread_height']

    def add(points, role, kind='outline', color='indigo'):
        rows.append({'points': np.asarray(points).tolist(), 'role': role, 'kind': kind, 'color': color})

    def satin(pairs, role, color):
        # One unbroken thread: stitches cross above cloth; travel passes below it.
        points = []
        for a, b in pairs:
            points.append([*a, -.012])
            for t in np.linspace(0, 1, 7):
                p = a*(1-t)+b*t
                points.append([*p, .002+loft*np.sin(np.pi*t)])
            points.append([*b, -.012])
        add(points, role, 'satin', color)

    for sx in (-1, 1):
        for sy in (-1, 1):
            center = np.array([sx*.46, sy*.32])*scale
            half = np.array([.215, .27])*scale
            corners = np.array([[0,1],[1,0],[0,-1],[-1,0],[0,1]])
            for index, size in enumerate((1, .82, .64, .46, .25)):
                add(center+corners*half*size, 'bone', color='pearl' if index%2 else 'indigo')
            for sector in range(4):
                angle = sector*np.pi/2
                rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
                pairs = []
                for t in np.linspace(.06, .9, 40):
                    left = np.array([-.2*(1-t), .27*t])*scale
                    right = np.array([.2*(1-t), .27*t])*scale
                    pairs.append((center+rotation@left, center+rotation@right))
                satin(pairs, 'bone', 'slate' if sector%2 else 'indigo')

            spine = bezier([[.025,.015],[.11,.77],[.80,.22],[1.04,.90]])
            spine *= [sx*scale, sy*scale]
            add(spine, 'feather', color='pearl')
            for band in range(7):
                root = spine[round((.035+band*.072)*(len(spine)-1))]
                tip = np.array([sx*(.89+band*.025), sy*(.12+band*.13)])*scale
                bend = np.array([sx*.12, sy*.18])*scale
                stem = bezier([root, root+bend, tip-np.array([sx*.18,sy*.10])*scale, tip], 65)
                tangent = np.gradient(stem, axis=0)
                tangent /= np.maximum(np.linalg.norm(tangent, axis=1)[:,None], 1e-8)
                normals = np.stack([-tangent[:,1], tangent[:,0]], axis=1)
                envelope = np.sin(np.linspace(0,np.pi,len(stem)))**.8*(.055+band*.003)*scale
                left, right = stem-normals*envelope[:,None], stem+normals*envelope[:,None]
                add(stem, 'feather', color='pearl')
                add(left, 'feather')
                add(right, 'feather', color='slate')
                pairs = []
                for i in range(1, len(stem)-1):
                    pairs.append((left[i], stem[min(i+2,len(stem)-1)]))
                    pairs.append((stem[max(i-2,0)], right[i]))
                satin(pairs, 'feather', 'slate' if band%2 else 'indigo')
            for i in range(16):
                root = spine[round((.18+i*.04)*(len(spine)-1))]
                tip = np.array([sx*(.50+i*.047), sy*(.79+i*.022)])*scale
                bend = np.array([sx*.17,sy*.05])*scale
                add(bezier([root,root+bend,tip-bend,tip]), 'feather')
            # Shared wing ribs connect the diamonds to the body instead of floating.
            add(bezier([[.018,.025],[.17,.08],[.28,.03],[.46,.05]])*[sx*scale,sy*scale], 'bone')
            add(bezier([[.018,.025],[.18,.25],[.23,.58],[.46,.59]])*[sx*scale,sy*scale], 'bone')

    t = np.linspace(0,1,65)
    for side in (-1,1):
        add(np.stack([side*.052*np.sin(np.pi*t), .47-.85*t],axis=1)*scale, 'bone')
        add(bezier([[side*.015,.38],[side*.025,.55],[side*.16,.73],[side*.20,.57]])*scale, 'bone')
    for y in np.linspace(-.36,.38,11):
        a = np.linspace(0,2*np.pi,33)
        add(np.stack([.047*np.cos(a),y+.025*np.sin(a)],axis=1)*scale,'bone',color='pearl')
    return rows
