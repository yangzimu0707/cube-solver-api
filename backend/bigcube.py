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

    # ---------- 面旋转（与前端一致）----------

    def rotate_face_cw(self, face):
        n = self.size
        old = self.get_face(face)
        new = [None] * (n * n)
        # new[col, n-1-row] = old[row, col]
        for row in range(n):
            for col in range(n):
                new[col * n + (n - 1 - row)] = old[row * n + col]
        self.set_face(face, new)

    def rotate_face_ccw(self, face):
        self.rotate_face_cw(face)
        self.rotate_face_cw(face)
        self.rotate_face_cw(face)

    # ---------- 外层转动（与前端一致）----------

    def turn_right(self):
        n = self.size
        max_idx = n - 1
        self.rotate_face_cw(RIGHT)

        u = [self.get_facelet(UP, i, max_idx) for i in range(n)]
        f = [self.get_facelet(FRONT, i, max_idx) for i in range(n)]
        d = [self.get_facelet(DOWN, i, max_idx) for i in range(n)]
        b = [self.get_facelet(BACK, max_idx - i, 0) for i in range(n)]

        for i in range(n):
            self.set_facelet(FRONT, i, max_idx, u[i])
            self.set_facelet(DOWN, i, max_idx, f[i])
            self.set_facelet(BACK, max_idx - i, 0, d[i])
            self.set_facelet(UP, i, max_idx, b[i])

    def turn_left(self):
        n = self.size
        max_idx = n - 1
        self.rotate_face_cw(LEFT)

        u = [self.get_facelet(UP, i, 0) for i in range(n)]
        b = [self.get_facelet(BACK, max_idx - i, max_idx) for i in range(n)]
        d = [self.get_facelet(DOWN, i, 0) for i in range(n)]
        f = [self.get_facelet(FRONT, i, 0) for i in range(n)]

        for i in range(n):
            self.set_facelet(FRONT, i, 0, u[i])
            self.set_facelet(DOWN, i, 0, f[i])
            self.set_facelet(BACK, max_idx - i, max_idx, d[i])
            self.set_facelet(UP, i, 0, b[i])

    def turn_up(self):
        n = self.size
        self.rotate_face_cw(UP)

        f = self.get_face(FRONT)
        r = self.get_face(RIGHT)
        b = self.get_face(BACK)
        l = self.get_face(LEFT)

        for i in range(n):
            self.set_facelet(RIGHT, 0, i, f[i])
            self.set_facelet(BACK, 0, i, r[i])
            self.set_facelet(LEFT, 0, i, b[i])
            self.set_facelet(FRONT, 0, i, l[i])

    def turn_down(self):
        n = self.size
        max_idx = n - 1
        self.rotate_face_cw(DOWN)

        f = self.get_face(FRONT)
        r = self.get_face(RIGHT)
        b = self.get_face(BACK)
        l = self.get_face(LEFT)

        for i in range(n):
            self.set_facelet(RIGHT, max_idx, i, f[max_idx * n + i])
            self.set_facelet(BACK, max_idx, i, r[max_idx * n + i])
            self.set_facelet(LEFT, max_idx, i, b[max_idx * n + i])
            self.set_facelet(FRONT, max_idx, i, l[max_idx * n + i])

    def turn_front(self):
        n = self.size
        max_idx = n - 1
        self.rotate_face_cw(FRONT)

        u = [self.get_facelet(UP, max_idx, i) for i in range(n)]
        l = [self.get_facelet(LEFT, max_idx - i, max_idx) for i in range(n)]
        d = [self.get_facelet(DOWN, 0, max_idx - i) for i in range(n)]
        r = [self.get_facelet(RIGHT, i, 0) for i in range(n)]

        for i in range(n):
            self.set_facelet(RIGHT, i, 0, u[i])
            self.set_facelet(DOWN, 0, i, l[i])
            self.set_facelet(LEFT, i, max_idx, d[i])
            self.set_facelet(UP, max_idx, i, r[i])

    def turn_back(self):
        n = self.size
        max_idx = n - 1
        self.rotate_face_cw(BACK)

        u = [self.get_facelet(UP, 0, i) for i in range(n)]
        r = [self.get_facelet(RIGHT, i, max_idx) for i in range(n)]
        d = [self.get_facelet(DOWN, max_idx, max_idx - i) for i in range(n)]
        l = [self.get_facelet(LEFT, max_idx - i, 0) for i in range(n)]

        for i in range(n):
            self.set_facelet(RIGHT, i, max_idx, u[i])
            self.set_facelet(DOWN, max_idx, i, r[i])
            self.set_facelet(LEFT, i, 0, d[i])
            self.set_facelet(UP, 0, i, l[i])

    # ---------- 内层转动（与前端一致）----------

    def turn_inner_x(self, layer_idx):
        """旋转垂直于 X 轴的层（x = layer_idx）"""
        n = self.size
        max_idx = n - 1

        u = [self.get_facelet(UP, i, layer_idx) for i in range(n)]
        f = [self.get_facelet(FRONT, i, layer_idx) for i in range(n)]
        d = [self.get_facelet(DOWN, i, layer_idx) for i in range(n)]
        b = [self.get_facelet(BACK, max_idx - i, max_idx - layer_idx) for i in range(n)]

        for i in range(n):
            self.set_facelet(FRONT, i, layer_idx, u[i])
            self.set_facelet(DOWN, i, layer_idx, f[i])
            self.set_facelet(BACK, max_idx - i, max_idx - layer_idx, d[i])
            self.set_facelet(UP, i, layer_idx, b[i])

    def turn_inner_y(self, layer_idx):
        """旋转垂直于 Y 轴的层（y = layer_idx）"""
        n = self.size
        max_idx = n - 1

        f = self.get_face(FRONT)
        r = self.get_face(RIGHT)
        b = self.get_face(BACK)
        l = self.get_face(LEFT)

        # F面该行 -> R面该行
        for i in range(n):
            self.set_facelet(RIGHT, layer_idx, i, f[layer_idx * n + i])
        # R面该行 -> B面该行
        for i in range(n):
            self.set_facelet(BACK, layer_idx, i, r[layer_idx * n + i])
        # B面该行 -> L面该行
        for i in range(n):
            self.set_facelet(LEFT, layer_idx, i, b[layer_idx * n + i])
        # L面该行 -> F面该行
        for i in range(n):
            self.set_facelet(FRONT, layer_idx, i, l[layer_idx * n + i])

    def turn_inner_z(self, layer_idx):
        """旋转垂直于 Z 轴的层（z = layer_idx）"""
        n = self.size
        max_idx = n - 1

        u = [self.get_facelet(UP, layer_idx, i) for i in range(n)]
        r = [self.get_facelet(RIGHT, i, layer_idx) for i in range(n)]
        d = [self.get_facelet(DOWN, max_idx - layer_idx, max_idx - i) for i in range(n)]
        l = [self.get_facelet(LEFT, max_idx - i, max_idx - layer_idx) for i in range(n)]

        for i in range(n):
            self.set_facelet(RIGHT, i, layer_idx, u[i])
            self.set_facelet(DOWN, max_idx - layer_idx, max_idx - i, r[i])
            self.set_facelet(LEFT, max_idx - i, max_idx - layer_idx, d[i])
            self.set_facelet(UP, layer_idx, i, l[i])

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
            self.turn_right(); self.turn_inner_x(n - 2)
        elif m == "TR'":
            self.turn_right(); self.turn_right(); self.turn_right()
            self.turn_inner_x(n - 2); self.turn_inner_x(n - 2); self.turn_inner_x(n - 2)
        elif m == "TR2":
            self.turn_right(); self.turn_right()
            self.turn_inner_x(n - 2); self.turn_inner_x(n - 2)
        elif m == "TL":
            self.turn_left(); self.turn_inner_x(1)
        elif m == "TL'":
            self.turn_left(); self.turn_left(); self.turn_left()
            self.turn_inner_x(1); self.turn_inner_x(1); self.turn_inner_x(1)
        elif m == "TL2":
            self.turn_left(); self.turn_left()
            self.turn_inner_x(1); self.turn_inner_x(1)
        elif m == "MR":
            self.turn_inner_x(n - 2)
        elif m == "MR'":
            self.turn_inner_x(n - 2); self.turn_inner_x(n - 2); self.turn_inner_x(n - 2)
        elif m == "MR2":
            self.turn_inner_x(n - 2); self.turn_inner_x(n - 2)
        elif m == "ML":
            self.turn_inner_x(1)
        elif m == "ML'":
            self.turn_inner_x(1); self.turn_inner_x(1); self.turn_inner_x(1)
        elif m == "ML2":
            self.turn_inner_x(1); self.turn_inner_x(1)
        elif m == "TU":
            self.turn_up(); self.turn_inner_y(n - 2)
        elif m == "TU'":
            self.turn_up(); self.turn_up(); self.turn_up()
            self.turn_inner_y(n - 2); self.turn_inner_y(n - 2); self.turn_inner_y(n - 2)
        elif m == "TU2":
            self.turn_up(); self.turn_up()
            self.turn_inner_y(n - 2); self.turn_inner_y(n - 2)
        elif m == "TD":
            self.turn_down(); self.turn_inner_y(1)
        elif m == "TD'":
            self.turn_down(); self.turn_down(); self.turn_down()
            self.turn_inner_y(1); self.turn_inner_y(1); self.turn_inner_y(1)
        elif m == "TD2":
            self.turn_down(); self.turn_down()
            self.turn_inner_y(1); self.turn_inner_y(1)
        elif m == "MU":
            self.turn_inner_y(n - 2)
        elif m == "MU'":
            self.turn_inner_y(n - 2); self.turn_inner_y(n - 2); self.turn_inner_y(n - 2)
        elif m == "MU2":
            self.turn_inner_y(n - 2); self.turn_inner_y(n - 2)
        elif m == "MD":
            self.turn_inner_y(1)
        elif m == "MD'":
            self.turn_inner_y(1); self.turn_inner_y(1); self.turn_inner_y(1)
        elif m == "MD2":
            self.turn_inner_y(1); self.turn_inner_y(1)
        elif m == "M":
            self.turn_inner_x(n // 2)
        elif m == "M'":
            self.turn_inner_x(n // 2); self.turn_inner_x(n // 2); self.turn_inner_x(n // 2)
        elif m == "M2":
            self.turn_inner_x(n // 2); self.turn_inner_x(n // 2)
        elif m == "E":
            self.turn_inner_y(n // 2)
        elif m == "E'":
            self.turn_inner_y(n // 2); self.turn_inner_y(n // 2); self.turn_inner_y(n // 2)
        elif m == "E2":
            self.turn_inner_y(n // 2); self.turn_inner_y(n // 2)
        elif m == "S":
            self.turn_inner_z(n // 2)
        elif m == "S'":
            self.turn_inner_z(n // 2); self.turn_inner_z(n // 2); self.turn_inner_z(n // 2)
        elif m == "S2":
            self.turn_inner_z(n // 2); self.turn_inner_z(n // 2)
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
