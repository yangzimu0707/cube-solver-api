"""
2x2 Rubik's Cube solver using BFS (Breadth-First Search)
Finds optimal solution (minimum moves)
"""

from collections import deque

# 2x2 cube representation:
# 24 stickers total, 6 faces with 4 stickers each
# Order: U(0-3), F(4-7), R(8-11), D(12-15), B(16-19), L(20-23)
# Face layout (looking at the face):
# 0 1
# 2 3

def rotate_face_cw(state, face):
    """Rotate a face clockwise"""
    state = list(state)
    size = 4
    face_start = face * size
    
    # Rotate face stickers: 0->1->3->2->0
    f = state[face_start:face_start + size]
    state[face_start:face_start + size] = [f[2], f[0], f[3], f[1]]
    
    return tuple(state)

def rotate_face_ccw(state, face):
    """Rotate a face counter-clockwise"""
    state = rotate_face_cw(state, face)
    state = rotate_face_cw(state, face)
    state = rotate_face_cw(state, face)
    return state

def apply_U(state):
    """U move: rotate up face clockwise"""
    state = rotate_face_cw(state, 0)
    # Cycle: F[0,1] -> L[0,1] -> B[0,1] -> R[0,1] -> F[0,1]
    f0, f1 = state[4], state[5]
    l0, l1 = state[20], state[21]
    b0, b1 = state[16], state[17]
    r0, r1 = state[8], state[9]
    
    state = list(state)
    state[4], state[5] = r0, r1
    state[20], state[21] = f0, f1
    state[16], state[17] = l0, l1
    state[8], state[9] = b0, b1
    return tuple(state)

def apply_D(state):
    """D move: rotate down face clockwise"""
    state = rotate_face_cw(state, 3)
    # Cycle: F[2,3] -> R[2,3] -> B[2,3] -> L[2,3] -> F[2,3]
    f2, f3 = state[6], state[7]
    r2, r3 = state[10], state[11]
    b2, b3 = state[18], state[19]
    l2, l3 = state[22], state[23]
    
    state = list(state)
    state[6], state[7] = l2, l3
    state[10], state[11] = f2, f3
    state[18], state[19] = r2, r3
    state[22], state[23] = b2, b3
    return tuple(state)

def apply_R(state):
    """R move: rotate right face clockwise"""
    state = rotate_face_cw(state, 2)
    # Cycle: F[1,3] -> D[1,3] -> B[1,3] (reversed) -> U[1,3] -> F[1,3]
    f1, f3 = state[5], state[7]
    d1, d3 = state[13], state[15]
    b1, b3 = state[17], state[19]
    u1, u3 = state[1], state[3]
    
    state = list(state)
    state[5], state[7] = u1, u3
    state[13], state[15] = f1, f3
    state[17], state[19] = d3, d1  # B is reversed
    state[1], state[3] = b3, b1
    return tuple(state)

def apply_L(state):
    """L move: rotate left face clockwise"""
    state = rotate_face_cw(state, 5)
    # Cycle: F[0,2] -> U[0,2] -> B[0,2] (reversed) -> D[0,2] -> F[0,2]
    f0, f2 = state[4], state[6]
    u0, u2 = state[0], state[2]
    b0, b2 = state[16], state[18]
    d0, d2 = state[12], state[14]
    
    state = list(state)
    state[4], state[6] = d0, d2
    state[0], state[2] = f0, f2
    state[16], state[18] = u2, u0  # B is reversed
    state[12], state[14] = b2, b0
    return tuple(state)

def apply_F(state):
    """F move: rotate front face clockwise"""
    state = rotate_face_cw(state, 1)
    # Cycle: U[2,3] -> R[0,2] -> D[0,1] -> L[1,3] (reversed) -> U[2,3]
    u2, u3 = state[2], state[3]
    r0, r2 = state[8], state[10]
    d0, d1 = state[12], state[13]
    l1, l3 = state[21], state[23]
    
    state = list(state)
    state[2], state[3] = l3, l1  # L is reversed
    state[8], state[10] = u2, u3
    state[12], state[13] = r0, r2
    state[21], state[23] = d1, d0
    return tuple(state)

def apply_B(state):
    """B move: rotate back face clockwise"""
    state = rotate_face_cw(state, 4)
    # Cycle: U[0,1] -> L[0,2] -> D[2,3] -> R[1,3] (reversed) -> U[0,1]
    u0, u1 = state[0], state[1]
    l0, l2 = state[20], state[22]
    d2, d3 = state[14], state[15]
    r1, r3 = state[9], state[11]
    
    state = list(state)
    state[0], state[1] = r3, r1  # R is reversed
    state[20], state[22] = u0, u1
    state[14], state[15] = l2, l0
    state[9], state[11] = d3, d2
    return tuple(state)

# Move definitions
MOVES_222 = [
    ("U", apply_U),
    ("U'", lambda s: apply_U(apply_U(apply_U(s)))),
    ("D", apply_D),
    ("D'", lambda s: apply_D(apply_D(apply_D(s)))),
    ("R", apply_R),
    ("R'", lambda s: apply_R(apply_R(apply_R(s)))),
    ("L", apply_L),
    ("L'", lambda s: apply_L(apply_L(apply_L(s)))),
    ("F", apply_F),
    ("F'", lambda s: apply_F(apply_F(apply_F(s)))),
    ("B", apply_B),
    ("B'", lambda s: apply_B(apply_B(apply_B(s)))),
]

def solve_222(state_str):
    """
    Solve 2x2 cube using BFS
    state_str: 24-character string representing cube state
    Returns: list of moves
    """
    if len(state_str) != 24:
        raise ValueError(f"State string must be 24 characters, got {len(state_str)}")
    
    # Convert to tuple for hashing
    start_state = tuple(state_str)
    
    # Goal state: each face has same color
    goal_state = tuple(
        [state_str[0]] * 4 +  # U face
        [state_str[4]] * 4 +  # F face
        [state_str[8]] * 4 +  # R face
        [state_str[12]] * 4 + # D face
        [state_str[16]] * 4 + # B face
        [state_str[20]] * 4   # L face
    )
    
    if start_state == goal_state:
        return []
    
    # BFS
    queue = deque([(start_state, [])])
    visited = {start_state}
    
    while queue:
        state, moves = queue.popleft()
        
        # Try all moves
        for move_name, move_func in MOVES_222:
            new_state = move_func(state)
            
            if new_state == goal_state:
                return moves + [move_name]
            
            if new_state not in visited:
                visited.add(new_state)
                queue.append((new_state, moves + [move_name]))
                
                # Limit search depth (2x2 max 11 moves)
                if len(moves) >= 11:
                    continue
    
    return None  # No solution found
