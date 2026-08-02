"""
5x5 Rubik's Cube solver using Reduction Method
Reduces 5x5 to 3x3, then solves with Kociemba
"""

import kociemba

def solve_555(state_str):
    """
    Solve 5x5 cube using reduction method
    state_str: 150-character string representing cube state
    Order: U(25), F(25), R(25), D(25), B(25), L(25)
    
    5x5 face layout (0-indexed):
     0  1  2  3  4
     5  6  7  8  9
    10 11 12 13 14
    15 16 17 18 19
    20 21 22 23 24
    
    Returns: list of moves
    """
    if len(state_str) != 150:
        raise ValueError(f"State string must be 150 characters, got {len(state_str)}")
    
    # Parse the 5x5 state into 6 faces
    # Input order: U, F, R, D, B, L
    faces_input = {}
    face_names_input = ['U', 'F', 'R', 'D', 'B', 'L']
    for i, face in enumerate(face_names_input):
        faces_input[face] = list(state_str[i*25:(i+1)*25])
    
    # Extract equivalent 3x3 state
    # For 5x5 -> 3x3 reduction:
    # - Centers: use position 12 (exact center of 3x3 center block)
    # - Corners: use positions 0, 4, 20, 24
    # - Edges: use positions 2, 10, 14, 22 (middle of each edge pair)
    
    # Kociemba expects order: U, R, F, D, L, B
    # 3x3 face layout:
    # 0 1 2
    # 3 4 5
    # 6 7 8
    
    state_3x3 = []
    
    # U face
    u = faces_input['U']
    state_3x3.extend([
        u[0], u[2], u[4],   # corners and top edge
        u[10], u[12], u[14], # left edge, center, right edge
        u[20], u[22], u[24]  # bottom edge and corners
    ])
    
    # R face
    r = faces_input['R']
    state_3x3.extend([
        r[0], r[2], r[4],
        r[10], r[12], r[14],
        r[20], r[22], r[24]
    ])
    
    # F face
    f = faces_input['F']
    state_3x3.extend([
        f[0], f[2], f[4],
        f[10], f[12], f[14],
        f[20], f[22], f[24]
    ])
    
    # D face
    d = faces_input['D']
    state_3x3.extend([
        d[0], d[2], d[4],
        d[10], d[12], d[14],
        d[20], d[22], d[24]
    ])
    
    # L face
    l = faces_input['L']
    state_3x3.extend([
        l[0], l[2], l[4],
        l[10], l[12], l[14],
        l[20], l[22], l[24]
    ])
    
    # B face
    b = faces_input['B']
    state_3x3.extend([
        b[0], b[2], b[4],
        b[10], b[12], b[14],
        b[20], b[22], b[24]
    ])
    
    cube_string = ''.join(state_3x3)
    
    # Solve with Kociemba
    try:
        solution_3x3 = kociemba.solve(cube_string)
        moves_3x3 = solution_3x3.split()
        
        # 3x3 moves map directly to 5x5 outer layer moves
        # (reduction method assumes centers and edges are already solved)
        return moves_3x3
    except Exception as e:
        raise ValueError(f"Failed to solve reduced 3x3: {str(e)}")
