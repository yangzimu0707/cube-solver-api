"""
4x4 / 5x5 魔方状态模型。

本模块是 iOS 前端 CubeModel.swift 转层逻辑的忠实移植，
保证后端求解器与前端 App 的魔方朝向/坐标完全一致，
这样后端返回的动作序列在 App 里才能正确还原魔方。

坐标约定（与前端一致）：
- 面索引: up=0, down=1, front=2, back=3, left=4, right=5
- 输入字符串面顺序: U, F, R, D, B, L（每个面按行优先输出 n*n 个贴纸）
- 单面贴纸索引: facelet[face*size*size + row*size + col]
"""

# 面索引常量
UP = 0
DOWN = 1
FRONT = 2
BACK = 3
LEFT = 4
RIGHT = 5

FACE_NAMES = ["U", "D", "F", "B", "L", "R"]

# 输入字符串的面顺序 -> 内部面索引
# 输入顺序: U, F, R, D, B, L
INPUT_FACES = [UP, FRONT, RIGHT, DOWN, BACK, LEFT]


class BigCube:
    def __init__(self, size, state_str):
        """
        state_str: 长度 size*size*6 的字符串，面顺序 U, F, R, D, B, L，
                   每面按行优先。
        """
        self.size = size
        n = size
        if len(state_str) != n * n * 6:
            raise ValueError(
                "State string must be %d characters, got %d"
                % (n * n * 6, len(state_str))
            )
        # 内部存储顺序: up, down, front, back, left, right
        facelets = []
        for internal_face in range(6):
            # 找到输入顺序中的段
            seg_idx = INPUT_FACES.index(internal_face)
            seg = state_str[seg_idx * n * n:(seg_idx + 1) * n * n]
            facelets.extend(seg)
        self.facelets = list(facelets)

    # ---------- 基础访问 ----------

    def _offset(self, face):
        return face * self.size * self.size

    def get_face(self, face):
        start = self._offset(face)
        n2 = self.size * self.size
        return list(self.facelets[start:start + n2])

    def set_face(self, face, values):
        start = self._offset(face)
        n2 = self.size * self.size
        self.facelets[start:start + n2] = list(values)

    def get_facelet(self, face, row, col):
        return self.facelets[self._offset(face) + row * self.size + col]

    def set_facelet(self, face, row, col, value):
        self.facelets[self._offset(face) + row * self.size + col] = value

    # ---------- 序列化（与前端 toCubeString 一致：U, F, R, D, B, L）----------

    def serialize(self):
        n = self.size
        result = []
        for face in INPUT_FACES:
            result.extend(self.get_face(face))
        return "".join(result)

    # ---------- 刚体层转动（与前端 3D 动画一致） ----------
    #
    # 语义经 kociemba 端到端验证（backend/test_std.py 候选 B）：
    #   R/U/F 使用 dir=-1，L/D/B 使用 dir=+1
    #   （dir=+1 为轴正方向看逆时针；等效于"从该面外侧看顺时针"的标准魔方动作）
    # 贴纸坐标约定 = 前端 color-getter（getUpFaceColor 等），与 3D 动画刚体旋转完全一致。

    def _face_normal(self, face):
        return {
            UP: (0, 1, 0), DOWN: (0, -1, 0), FRONT: (0, 0, 1),
            BACK: (0, 0, -1), LEFT: (-1, 0, 0), RIGHT: (1, 0, 0),
        }[face]

    def _facelet_pos(self, f, r, c):
        """贴纸 (f,r,c) -> 物理坐标 (x,y,z)，与前端 getXxxFaceColor 一致"""
        n = self.size
        m = n - 1
        if f == UP: return (c, m, r)
        if f == DOWN: return (c, 0, m - r)
        if f == FRONT: return (c, m - r, m)
        if f == BACK: return (m - c, m - r, 0)
        if f == LEFT: return (0, m - r, c)
        return (m, m - r, m - c)  # RIGHT

    def _rot_point(self, axis, d, p):
        """绕 axis 轴旋转 dir（右手正 90° 为 dir=+1）"""
        x, y, z = p
        cx = cy = cz = (self.size - 1) / 2.0
        dx, dy, dz = x - cx, y - cy, z - cz
        if axis == 0:
            return (x, cy - dz * d, cz + dy * d)
        if axis == 1:
            return (cx + dz * d, y, cz - dx * d)
        return (cx - dy * d, cy + dx * d, z)

    def _rot_normal(self, axis, d, nv):
        nx, ny, nz = nv
        if axis == 0: return (nx, -nz * d, ny * d)
        if axis == 1: return (nz * d, ny, -nx * d)
        return (-ny * d, nx * d, nz)

    def _pos_to_facelet(self, q, nv):
        """物理坐标 + 贴纸法线 -> (face, row, col)"""
        n = self.size
        m = n - 1
        x = int(round(q[0])); y = int(round(q[1])); z = int(round(q[2]))
        if nv == (0, 1, 0):  return UP, z, x
        if nv == (0, -1, 0): return DOWN, m - z, x
        if nv == (0, 0, 1):  return FRONT, m - y, x
        if nv == (0, 0, -1): return BACK, m - y, m - x
        if nv == (-1, 0, 0): return LEFT, m - y, z
        return RIGHT, m - y, m - z

    def _turn_layer(self, axis, fixed_layer, d):
        """通用刚体层转动：垂直于 axis 轴、坐标=fixed_layer 的层绕 axis 旋转 dir"""
        n = self.size
        old = list(self.facelets)
        moves = []
        for f in range(6):
            for r in range(n):
                for c in range(n):
                    p = self._facelet_pos(f, r, c)
                    if p[axis] != fixed_layer:
                        continue
                    q = self._rot_point(axis, d, p)
                    nv = self._rot_normal(axis, d, self._face_normal(f))
                    df, dr, dc = self._pos_to_facelet(q, nv)
                    moves.append((f * n * n + r * n + c, df * n * n + dr * n + dc))
        for src, dst in moves:
            self.facelets[dst] = old[src]

    # ---------- 外层转动（与前端 3D 动画一致） ----------

    def turn_right(self):
        self._turn_layer(0, self.size - 1, -1)

    def turn_left(self):
        self._turn_layer(0, 0, 1)

    def turn_up(self):
        self._turn_layer(1, self.size - 1, -1)

    def turn_down(self):
        self._turn_layer(1, 0, 1)

    def turn_front(self):
        self._turn_layer(2, self.size - 1, -1)

    def turn_back(self):
        self._turn_layer(2, 0, 1)

    # ---------- 内层转动（与前端 3D 动画一致） ----------

    def turn_inner_x(self, layer_idx, d):
        self._turn_layer(0, layer_idx, d)

    def turn_inner_y(self, layer_idx, d):
        self._turn_layer(1, layer_idx, d)

    def turn_inner_z(self, layer_idx, d):
        self._turn_layer(2, layer_idx, d)

    # ---------- 动作映射（与前端 applyMove 一致）----------

    def apply(self, move_name):
        """
        应用单个动作。move_name 使用前端枚举的字符串形式：
        U, U', U2, D, D', D2, F, F', F2, B, B', B2, L, L', L2, R, R', R2,
        TR, TR', TR2, TL, TL', TL2, TU, TU', TU2, TD, TD', TD2,
        MR, MR', MR2, ML, ML', ML2, MU, MU', MU2, MD, MD', MD2,
        M, M', M2, E, E', E2, S, S', S2
        """
        n = self.size
        m = move_name

        # 外层基本动作
        if m == "R":
            self.turn_right()
        elif m == "R'":
            self.turn_right(); self.turn_right(); self.turn_right()
        elif m == "R2":
            self.turn_right(); self.turn_right()
        elif m == "L":
            self.turn_left()
        elif m == "L'":
            self.turn_left(); self.turn_left(); self.turn_left()
        elif m == "L2":
            self.turn_left(); self.turn_left()
        elif m == "U":
            self.turn_up()
        elif m == "U'":
            self.turn_up(); self.turn_up(); self.turn_up()
        elif m == "U2":
            self.turn_up(); self.turn_up()
        elif m == "D":
            self.turn_down()
        elif m == "D'":
            self.turn_down(); self.turn_down(); self.turn_down()
        elif m == "D2":
            self.turn_down(); self.turn_down()
        elif m == "F":
            self.turn_front()
        elif m == "F'":
            self.turn_front(); self.turn_front(); self.turn_front()
        elif m == "F2":
            self.turn_front(); self.turn_front()
        elif m == "B":
            self.turn_back()
        elif m == "B'":
            self.turn_back(); self.turn_back(); self.turn_back()
        elif m == "B2":
            self.turn_back(); self.turn_back()

        # 宽层 / 内层 / 中间层动作
        elif m == "TR":
            self.turn_right(); self.turn_inner_x(n - 2, -1)
        elif m == "TR'":
            self.turn_right(); self.turn_right(); self.turn_right()
            self.turn_inner_x(n - 2, -1); self.turn_inner_x(n - 2, -1); self.turn_inner_x(n - 2, -1)
        elif m == "TR2":
            self.turn_right(); self.turn_right()
            self.turn_inner_x(n - 2, -1); self.turn_inner_x(n - 2, -1)
        elif m == "TL":
            self.turn_left(); self.turn_inner_x(1, 1)
        elif m == "TL'":
            self.turn_left(); self.turn_left(); self.turn_left()
            self.turn_inner_x(1, 1); self.turn_inner_x(1, 1); self.turn_inner_x(1, 1)
        elif m == "TL2":
            self.turn_left(); self.turn_left()
            self.turn_inner_x(1, 1); self.turn_inner_x(1, 1)
        elif m == "MR":
            self.turn_inner_x(n - 2, -1)
        elif m == "MR'":
            self.turn_inner_x(n - 2, -1); self.turn_inner_x(n - 2, -1); self.turn_inner_x(n - 2, -1)
        elif m == "MR2":
            self.turn_inner_x(n - 2, -1); self.turn_inner_x(n - 2, -1)
        elif m == "ML":
            self.turn_inner_x(1, 1)
        elif m == "ML'":
            self.turn_inner_x(1, 1); self.turn_inner_x(1, 1); self.turn_inner_x(1, 1)
        elif m == "ML2":
            self.turn_inner_x(1, 1); self.turn_inner_x(1, 1)
        elif m == "TU":
            self.turn_up(); self.turn_inner_y(n - 2, -1)
        elif m == "TU'":
            self.turn_up(); self.turn_up(); self.turn_up()
            self.turn_inner_y(n - 2, -1); self.turn_inner_y(n - 2, -1); self.turn_inner_y(n - 2, -1)
        elif m == "TU2":
            self.turn_up(); self.turn_up()
            self.turn_inner_y(n - 2, -1); self.turn_inner_y(n - 2, -1)
        elif m == "TD":
            self.turn_down(); self.turn_inner_y(1, 1)
        elif m == "TD'":
            self.turn_down(); self.turn_down(); self.turn_down()
            self.turn_inner_y(1, 1); self.turn_inner_y(1, 1); self.turn_inner_y(1, 1)
        elif m == "TD2":
            self.turn_down(); self.turn_down()
            self.turn_inner_y(1, 1); self.turn_inner_y(1, 1)
        elif m == "MU":
            self.turn_inner_y(n - 2, -1)
        elif m == "MU'":
            self.turn_inner_y(n - 2, -1); self.turn_inner_y(n - 2, -1); self.turn_inner_y(n - 2, -1)
        elif m == "MU2":
            self.turn_inner_y(n - 2, -1); self.turn_inner_y(n - 2, -1)
        elif m == "MD":
            self.turn_inner_y(1, 1)
        elif m == "MD'":
            self.turn_inner_y(1, 1); self.turn_inner_y(1, 1); self.turn_inner_y(1, 1)
        elif m == "MD2":
            self.turn_inner_y(1, 1); self.turn_inner_y(1, 1)
        elif m == "M":
            self.turn_inner_x((n - 1) // 2, -1)
        elif m == "M'":
            self.turn_inner_x((n - 1) // 2, -1); self.turn_inner_x((n - 1) // 2, -1); self.turn_inner_x((n - 1) // 2, -1)
        elif m == "M2":
            self.turn_inner_x((n - 1) // 2, -1); self.turn_inner_x((n - 1) // 2, -1)
        elif m == "E":
            self.turn_inner_y((n - 1) // 2, -1)
        elif m == "E'":
            self.turn_inner_y((n - 1) // 2, -1); self.turn_inner_y((n - 1) // 2, -1); self.turn_inner_y((n - 1) // 2, -1)
        elif m == "E2":
            self.turn_inner_y((n - 1) // 2, -1); self.turn_inner_y((n - 1) // 2, -1)
        elif m == "S":
            self.turn_inner_z((n - 1) // 2, -1)
        elif m == "S'":
            self.turn_inner_z((n - 1) // 2, -1); self.turn_inner_z((n - 1) // 2, -1); self.turn_inner_z((n - 1) // 2, -1)
        elif m == "S2":
            self.turn_inner_z((n - 1) // 2, -1); self.turn_inner_z((n - 1) // 2, -1)
        else:
            raise ValueError("Unknown move: %s" % m)

    def apply_moves(self, moves):
        for m in moves:
            self.apply(m)

    # ---------- 判断 ----------

    def is_solved(self):
        n = self.size
        n2 = n * n
        for face in range(6):
            values = self.get_face(face)
            first = values[0]
            if any(v != first for v in values):
                return False
        return True

    # ---------- 中心块 ----------

    def center_positions(self):
        """返回每个面的中心块位置列表 [(row, col), ...]"""
        n = self.size
        if n == 4:
            rows = [1, 2]
            cols = [1, 2]
        else:  # n == 5
            rows = [1, 2, 3]
            cols = [1, 2, 3]
        result = {}
        for face in range(6):
            positions = []
            for r in rows:
                for c in cols:
                    positions.append((r, c))
            result[face] = positions
        return result

    def center_colors(self):
        """每个面中心块当前颜色集合（用于识别面颜色）"""
        pos = self.center_positions()
        colors = {}
        for face in range(6):
            colors[face] = set(self.get_facelet(face, r, c) for (r, c) in pos[face])
        return colors

    def center_solved(self):
        """检查 6 个中心块是否都单色（每面中心块颜色一致）"""
        pos = self.center_positions()
        for face in range(6):
            first = self.get_facelet(face, pos[face][0][0], pos[face][0][1])
            for (r, c) in pos[face]:
                if self.get_facelet(face, r, c) != first:
                    return False
        return True


def cube_from_solved(size):
    """构造一个已还原的魔方状态字符串（U,F,R,D,B,L 顺序）"""
    faces = []
    for face in INPUT_FACES:
        n2 = size * size
        faces.append(FACE_NAMES[face] * n2)
    return "".join(faces)
