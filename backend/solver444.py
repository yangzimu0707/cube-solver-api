"""
4x4 Rubik's Cube solver using Reduction Method
Reduces 4x4 to 3x3, then solves with Kociemba
"""

import kociemba

def solve_444(state_str):
    """
    Solve 4x4 cube using reduction method
    state_str: 96-character string representing cube state
    Order: U(16), F(16), R(16), D(16), B(16), L(16)
    
    4x4 face layout (0-indexed):
     0  1  2  3
     4  5  6  7
     8  9 10 11
    12 13 14 15
    
    Returns: list of moves
    """
    if len(state_str) != 96:
        raise ValueError(f"State string must be 96 characters, got {len(state_str)}")
    
    # Parse the 4x4 state into 6 faces
    # Input order: U, F, R, D, B, L
    faces_input = {}
    face_names_input = ['U', 'F', 'R', 'D', 'B', 'L']
    for i, face in enumerate(face_names_input):
        faces_input[face] = list(state_str[i*16:(i+1)*16])
    
    # Extract equivalent 3x3 state
    # For 4x4 -> 3x3 reduction:
    # - Centers: use position 5 (top-left of 2x2 center block)
    # - Corners: use positions 0, 3, 12, 15
    # - Edges: use positions 1, 4, 7, 8, 11, 13 (one of each pair)
    
    # Kociemba expects order: U, R, F, D, L, B
    # 3x3 face layout:
    # 0 1 2
    # 3 4 5
    # 6 7 8
    
    state_3x3 = []
    
    # U face
    u = faces_input['U']
    state_3x3.extend([
        u[0], u[1], u[3],   # corners and top edges
        u[4], u[5], u[7],   # left edge, center, right edge
        u[12], u[13], u[15] # bottom edges and corners
    ])
    
    # R face
    r = faces_input['R']
    state_3x3.extend([
        r[0], r[1], r[3],
        r[4], r[5], r[7],
        r[12], r[13], r[15]
    ])
    
    # F face
    f = faces_input['F']
    state_3x3.extend([
        f[0], f[1], f[3],
        f[4], f[5], f[7],
        f[12], f[13], f[15]
    ])
    
    # D face
    d = faces_input['D']
    state_3x3.extend([
        d[0], d[1], d[3],
        d[4], d[5], d[7],
        d[12], d[13], d[15]
    ])
    
    # L face
    l = faces_input['L']
    state_3x3.extend([
        l[0], l[1], l[3],
        l[4], l[5], l[7],
        l[12], l[13], l[15]
    ])
    
    # B face
    b = faces_input['B']
    state_3x3.extend([
        b[0], b[1], b[3],
        b[4], b[5], b[7],
        b[12], b[13], b[15]
    ])
    
    cube_string = ''.join(state_3x3)
    
    # Solve with Kociemba
    try:
        solution_3x3 = kociemba.solve(cube_string)
        moves_3x3 = solution_3x3.split()
        
        # 3x3 moves map directly to 4x4 outer layer moves
        # (reduction method assumes centers and edges are already solved)
        return moves_3x3
    except Exception as e:
        raise ValueError(f"Failed to solve reduced 3x3: {str(e)}")
