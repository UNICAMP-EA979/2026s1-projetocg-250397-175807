import numpy as np
import urenderer
from OpenGL import GL
from urenderer.geometry.mesh import get_mesh_cube, get_mesh_sphere
from urenderer.node import Node
from urenderer.renderer.opengl import Material, Texture

# Helpers de textura

def solid_color_texture(rgb: tuple[int, int, int]) -> Texture:
    '''Textura 1x1 de uma cor sólida (para baseColor).'''
    data = np.array([[rgb]], dtype=np.uint8)
    return Texture(data, GL.GL_RGB, GL.GL_RGB)


def solid_value_texture(value: int) -> Texture:
    '''Textura 1x1 de um canal só (para metallic/roughness).'''
    data = np.array([[value]], dtype=np.uint8)
    return Texture(data, GL.GL_RED, GL.GL_R8)


def mirror_ball_texture(n_tiles: int = 16, tile_px: int = 16) -> Texture:
    '''
    Gera um padrão xadrez de tons prateados, simulando os pequenos espelhos
    quadrados de um globo de espelhos.
    '''
    size = n_tiles * tile_px
    data = np.empty((size, size, 3), dtype=np.uint8)

    light = np.array([238, 240, 245], dtype=np.uint8)
    dark = np.array([150, 155, 165], dtype=np.uint8)

    for i in range(n_tiles):
        for j in range(n_tiles):
            color = light if (i + j) % 2 == 0 else dark
            data[i*tile_px:(i+1)*tile_px, j*tile_px:(j+1)*tile_px] = color

    return Texture(data, GL.GL_RGB, GL.GL_RGB)


# Animações

JUMP_PERIOD = 2.0        # segundos por pulo
JUMP_HEIGHT = 0.2        # altura do pulo
FLOOR_PERIOD = 1.0       # segundos por troca cor do piso


def update_jump(node: Node, delta_time: float, time_since_start: float) -> None:
    '''Faz o boneco pular continuamente, com um leve achtamento e esticamento.'''
    phase = (time_since_start % JUMP_PERIOD) / JUMP_PERIOD
    bounce = np.abs(np.sin(np.pi * phase))  # 0 depois 1 depois 0

    node.translation[1] = node.base_translation[1] + JUMP_HEIGHT * bounce

    # Esticado no ar, achatado ao tocar o chão
    stretch = 1.0 + 0.05 * bounce
    squash = 1.0 / np.sqrt(stretch)
    node.scale = np.array([squash, stretch, squash])

def update_change_color(node: Node, delta_time:float, time_since_start: float) -> None:
    '''Muda cor do floor'''
    period = int(time_since_start/FLOOR_PERIOD)

    if (node.last_period == None or node.last_period < period):
        node.last_period = period
        if (node.render_data["material"] is red_material):
            node.render_data["material"] = yellow_material
        elif (node.render_data["material"] is green_material):
            node.render_data["material"] = blue_material
        elif (node.render_data["material"] is blue_material):
            node.render_data["material"] = red_material
        else:
            node.render_data["material"] = green_material


def update_arm_swing(node: Node, delta_time: float, time_since_start: float) -> None:
    '''Levanta os bracos conforme o boneco pula, tipo uma animação "comemorando".'''
    phase = (time_since_start % JUMP_PERIOD) / JUMP_PERIOD
    bounce = np.abs(np.sin(np.pi * phase))

    node.rotation[0] = node.swing_sign * (100.0 * bounce)


def update_leg_kick(node: Node, delta_time: float, time_since_start: float) -> None:
    '''Recolhe levemente as pernas no ar, como um pulinho animado kkkk'''
    phase = (time_since_start % JUMP_PERIOD) / JUMP_PERIOD
    bounce = np.abs(np.sin(np.pi * phase))

    node.rotation[0] = node.kick_sign * (25.0 * bounce)


def update_disco_spin(node: Node, delta_time: float, time_since_start: float) -> None:
    '''Gira o globo de espelhos continuamente em torno do eixo Y.'''
    node.rotation[1] = (30.0 * time_since_start) % 360.0

# Construcao do boneco feito inteiramente de cubos pra não ficar muito complicado

# Dimensoes do corpo (em unidades de cena)
LEG_W, LEG_H = 0.28, 0.8
SHOE_W, SHOE_H = 0.35, 0.26
TORSO_W, TORSO_H, TORSO_D = 0.7, 0.9, 0.4
ARM_W, ARM_H = 0.24, 0.75
SLEEVE_W, SLEEVE_H = 0.3, 0.3
HEAD_S = 0.55
EYES_S = 0.05
HAT_TIP_W, HAT_TIP_H = 0.7, 0.05
HAT_TOP_W, HAT_TOP_H = 0.4, 0.3


def make_cube_node(name: str, size: tuple[float, float, float],
                    local_offset: tuple[float, float, float],
                    material: Material, cube_mesh) -> Node:
    '''Cria um nó de cubo com escala/posição locais e material dado.'''
    node = Node(name)
    node.translation = np.array(local_offset, dtype=np.float64)
    node.scale = np.array(size, dtype=np.float64)
    node.render_data["mesh"] = cube_mesh
    node.render_data["material"] = material
    return node


def build_boneco(cube_mesh, skin_material: Material,
                  shirt_material: Material, pants_material: Material, shoes_material: Material, black_material: Material, red_material: Material) -> Node:
    '''
    Monta um boneco articulado feito só de cubos:

    root
     |- left_leg_joint  -> perna esquerda
     |- right_leg_joint -> perna direita
     |- torso
     |- head
     |- left_arm_joint  -> braço esquerdo
     |- right_arm_joint -> braço direito
    '''
    root = Node("boneco")
    root.base_translation = np.array([0.0, 0.0, 0.0])
    root.translation = root.base_translation.copy()
    root.callbacks = [update_jump]

    hip_y = LEG_H  # altura do quadril (topo das pernas)

    # Parte que faz as pernas (junta no quadril, cubo pendurado para baixo)
    for side, sign in (("left", -1.0), ("right", 1.0)):
        leg_joint = Node(f"{side}_leg_joint")
        leg_joint.translation = np.array(
            [sign * (LEG_W/2 + 0.02), hip_y, 0.0])
        leg_joint.kick_sign = -sign
        leg_joint.callbacks = [update_leg_kick]
        root.add_child(leg_joint)

        leg = make_cube_node(f"{side}_leg", (LEG_W, LEG_H, LEG_W),
                              (0.0, -LEG_H/2, 0.0), pants_material, cube_mesh)
        leg_joint.add_child(leg)

        # Sapatos
        shoe = make_cube_node(f"{side}_shoe", (SHOE_W, SHOE_H, SHOE_W),
                                (0.0, -(LEG_H - SHOE_H/2), 0.0), shoes_material, cube_mesh)
        leg_joint.add_child(shoe)

    # Torso
    torso = make_cube_node("torso", (TORSO_W, TORSO_H, TORSO_D),
                            (0.0, hip_y + TORSO_H/2, 0.0),
                            shirt_material, cube_mesh)
    root.add_child(torso)

    # Cabeça
    head = make_cube_node("head", (HEAD_S, HEAD_S, HEAD_S),
                           (0.0, hip_y + TORSO_H + HEAD_S/2, 0.0),
                           skin_material, cube_mesh)
    root.add_child(head)

    # Chapéu
    hat_tip = make_cube_node("hat_tip", (HAT_TIP_W, HAT_TIP_H, HAT_TIP_W),
                           (0.0, hip_y + TORSO_H + HEAD_S, 0.0),
                           black_material, cube_mesh)
    root.add_child(hat_tip)

    hat_top = make_cube_node("hat_top", (HAT_TOP_W - 0.01, HAT_TOP_H, HAT_TOP_W - 0.01),
                           (0.0, hip_y + TORSO_H + HEAD_S + HAT_TOP_H/2, 0.0),
                           black_material, cube_mesh)
    root.add_child(hat_top)

    hat_line = make_cube_node("hat_top", (HAT_TOP_W, HAT_TIP_H, HAT_TOP_W),
                           (0.0, hip_y + TORSO_H + HEAD_S + HAT_TIP_H, 0.0),
                           red_material, cube_mesh)
    root.add_child(hat_line)

    # Olhos
    eye_1 = make_cube_node("eye_1", (EYES_S, EYES_S, EYES_S),
                           (HEAD_S/6, hip_y + TORSO_H + HEAD_S/2, HEAD_S),
                           black_material, cube_mesh)
    root.add_child(eye_1)

    eye_2 = make_cube_node("eye_2", (EYES_S, EYES_S, EYES_S),
                           (-HEAD_S/6, hip_y + TORSO_H + HEAD_S/2, HEAD_S + EYES_S),
                           black_material, cube_mesh)
    root.add_child(eye_2)

    # Bracos (junta no ombro, cubo pendurado para baixo)
    shoulder_y = hip_y + TORSO_H - ARM_W/2
    for side, sign in (("left", -1.0), ("right", 1.0)):
        arm_joint = Node(f"{side}_arm_joint")
        arm_joint.translation = np.array(
            [sign * (TORSO_W/2 + ARM_W/2 + 0.02), shoulder_y, 0.0])
        arm_joint.swing_sign = -sign
        arm_joint.callbacks = [update_arm_swing]
        root.add_child(arm_joint)

        arm = make_cube_node(f"{side}_arm", (ARM_W, ARM_H, ARM_W),
                              (0.0, -ARM_H/2, 0.0), skin_material, cube_mesh)
        arm_joint.add_child(arm)

        # Manga
        manga = make_cube_node(f"{side}_manga", (SLEEVE_W, SLEEVE_H, SLEEVE_W),
                                (0.0, 0.0, 0.0), shirt_material, cube_mesh)
        arm_joint.add_child(manga)

    return root

# Cena

NOME_DA_CENA = "minha_cena"

if __name__ == "__main__":
    urenderer.utils.clear_workdir(NOME_DA_CENA)
    renderer = urenderer.renderer.OpenGLRenderer(1920, 1080)
    renderer.background_color = np.array([0.0, 0.0, 0.02, 1], np.float32)

    runtime = urenderer.application.Runtime(renderer, name=NOME_DA_CENA)

    # Luz ambiente bem baixa, tipo um clima de "salão escuro"
    renderer.ambient_color = np.array([0.03, 0.03, 0.05], dtype=np.float32)

    shader = urenderer.renderer.Shader("assets/vertex.vs", "assets/05-fragment.fs")

    # Texturas utilitárias
    black_r = solid_value_texture(0)
    white_r = solid_value_texture(255)
    matte_roughness = solid_value_texture(160)   # ~0.63, plástico fosco

    mirror_base = Texture.load_file(
        "assets/MirrorTiles_Color.jpg", srgb=True, drop_alpha=True)
    mirror_metallic = solid_value_texture(235)   # bem metálico
    mirror_roughness = solid_value_texture(20)   # bem liso para brilho forte

    # Materiais
    skin_material = Material(shader)
    skin_material.set_texture(0, "baseColorTexture", solid_color_texture((235, 190, 150)))
    skin_material.set_texture(1, "metallicTexture", black_r)
    skin_material.set_texture(2, "roughnessTexture", matte_roughness)
    skin_material.set_uniform("tiling", 1.0)

    shirt_material = Material(shader)
    shirt_material.set_texture(0, "baseColorTexture", solid_color_texture((220, 40, 60)))
    shirt_material.set_texture(1, "metallicTexture", black_r)
    shirt_material.set_texture(2, "roughnessTexture", matte_roughness)
    shirt_material.set_uniform("tiling", 1.0)

    pants_material = Material(shader)
    pants_material.set_texture(0, "baseColorTexture", solid_color_texture((40, 60, 140)))
    pants_material.set_texture(1, "metallicTexture", black_r)
    pants_material.set_texture(2, "roughnessTexture", matte_roughness)
    pants_material.set_uniform("tiling", 1.0)

    shoes_material = Material(shader)
    shoes_material.set_texture(0, "baseColorTexture", solid_color_texture((20, 10, 0)))
    shoes_material.set_texture(1, "metallicTexture", black_r)
    shoes_material.set_texture(2, "roughnessTexture", matte_roughness)
    shoes_material.set_uniform("tiling", 1.0)

    black_material = Material(shader)
    black_material.set_texture(0, "baseColorTexture", solid_color_texture((0, 0, 0)))
    black_material.set_texture(1, "metallicTexture", black_r)
    black_material.set_texture(2, "roughnessTexture", matte_roughness)
    black_material.set_uniform("tiling", 1.0)

    global red_material
    red_material = Material(shader)
    red_material.set_texture(0, "baseColorTexture", solid_color_texture((255, 0, 0)))
    red_material.set_texture(1, "metallicTexture", black_r)
    red_material.set_texture(2, "roughnessTexture", matte_roughness)
    red_material.set_uniform("tiling", 1.0)

    global green_material
    green_material = Material(shader)
    green_material.set_texture(0, "baseColorTexture", solid_color_texture((0, 255, 0)))
    green_material.set_texture(1, "metallicTexture", black_r)
    green_material.set_texture(2, "roughnessTexture", matte_roughness)
    green_material.set_uniform("tiling", 1.0)

    global blue_material
    blue_material = Material(shader)
    blue_material.set_texture(0, "baseColorTexture", solid_color_texture((0, 0, 255)))
    blue_material.set_texture(1, "metallicTexture", black_r)
    blue_material.set_texture(2, "roughnessTexture", matte_roughness)
    blue_material.set_uniform("tiling", 1.0)

    global yellow_material
    yellow_material = Material(shader)
    yellow_material.set_texture(0, "baseColorTexture", solid_color_texture((255, 255, 0)))
    yellow_material.set_texture(1, "metallicTexture", black_r)
    yellow_material.set_texture(2, "roughnessTexture", matte_roughness)
    yellow_material.set_uniform("tiling", 1.0)

    mirror_material = Material(shader)
    mirror_material.set_texture(0, "baseColorTexture", mirror_base)
    mirror_material.set_texture(1, "metallicTexture", mirror_metallic)
    mirror_material.set_texture(2, "roughnessTexture", mirror_roughness)
    mirror_material.set_uniform("tiling", 1.0)

    # Geometrias compartilhadas
    cube_mesh = get_mesh_cube()
    sphere_mesh = get_mesh_sphere()

    # Boneco, sozinho, pulando no meio da pista
    boneco = build_boneco(cube_mesh, skin_material, shirt_material, pants_material, shoes_material, black_material, red_material)
    boneco.base_translation = np.array([0.0, 0.0, -5.0])
    boneco.translation = boneco.base_translation.copy()
    runtime.scene.add_child(boneco)

    # Globo de espelhos, girando acima do boneco
    disco_ball = Node("disco_ball")
    disco_ball.translation = np.array([0.0, 3.8, -5.0])
    disco_ball.callbacks = [update_disco_spin]
    runtime.scene.add_child(disco_ball)

    ball_mesh_node = Node("disco_ball_mesh")
    ball_mesh_node.scale = np.array([0.7, 0.7, 0.7])
    ball_mesh_node.render_data["mesh"] = sphere_mesh
    ball_mesh_node.render_data["material"] = mirror_material
    disco_ball.add_child(ball_mesh_node)

    # Pequenas luzes coloridas presas ao globo que giram junto e espalham
    # reflexos coloridos pela pista, como um globo de espelhos de verdade.
    # Não ficaram perfeitas, mas é o que consegui
    ball_lights = [
        ((0.9, 0.0, 0.0), (1.0, 0.15, 0.15)),
        ((-0.9, 0.0, 0.0), (0.15, 1.0, 0.2)),
        ((0.0, 0.0, 0.9), (0.2, 0.4, 1.0)),
        ((0.0, 0.0, -0.9), (1.0, 0.2, 1.0)),
    ]
    for offset, color in ball_lights:
        light = urenderer.node.Light(urenderer.node.LightType.POINT)
        light.translation = np.array(offset, dtype=np.float64)
        light.light_color = np.array(color, dtype=np.float32)
        light.light_intensity = 3.0
        light.light_reference_distance = 1.5
        disco_ball.add_child(light)

    # Iluminação geral da cena
    key_light = urenderer.node.Light(urenderer.node.LightType.DIRECTIONAL)
    key_light.rotation = np.array([55, 25, 0], np.float64)
    key_light.light_color = np.array([0.6, 0.65, 0.9], np.float32)
    key_light.light_intensity = 1.5
    runtime.scene.add_child(key_light)

    spotlight = urenderer.node.Light(urenderer.node.LightType.POINT)
    spotlight.translation = np.array([0.0, 4.0, -3.0], np.float64)
    spotlight.light_color = np.array([1.0, 0.95, 0.85], np.float32)
    spotlight.light_intensity = 8.0
    spotlight.light_reference_distance = 2.0
    runtime.scene.add_child(spotlight)

    # Piso
    for side, sign in (("left", -1.0), ("right", 1.0)):
        floor_1 = Node(f"{side}_floor_1")
        floor_1.translation = np.array([-3.0, -0.05, -7.0])
        floor_1.scale = np.array([6.0, 0.1, 6.0])
        floor_1.render_data["mesh"] = cube_mesh
        floor_1.render_data["material"] = red_material
        floor_1.callbacks = [update_change_color]
        runtime.scene.add_child(floor_1)

        floor_2 = Node(f"{side}_floor_2")
        floor_2.translation = np.array([3.0, -0.05, -7.0])
        floor_2.scale = np.array([6.0, 0.1, 6.0])
        floor_2.render_data["mesh"] = cube_mesh
        floor_2.render_data["material"] = blue_material
        floor_2.callbacks = [update_change_color]
        runtime.scene.add_child(floor_2)

        floor_3 = Node(f"{side}_floor_3")
        floor_3.translation = np.array([3.0, -0.05, -1.0])
        floor_3.scale = np.array([6.0, 0.1, 6.0])
        floor_3.render_data["mesh"] = cube_mesh
        floor_3.render_data["material"] = green_material
        floor_3.callbacks = [update_change_color]
        runtime.scene.add_child(floor_3)

        floor_4 = Node(f"{side}_floor_4")
        floor_4.translation = np.array([-3.0, -0.05, -1.0])
        floor_4.scale = np.array([6.0, 0.1, 6.0])
        floor_4.render_data["mesh"] = cube_mesh
        floor_4.render_data["material"] = yellow_material
        floor_4.callbacks = [update_change_color]
        runtime.scene.add_child(floor_4)


    # Câmera
    runtime.camera.translation = np.array([0.0, 1.8, 2.0], np.float64)
    runtime.camera.rotation = np.array([-8.0, 0.0, 0.0], np.float64)
    runtime.camera.vertical_fov = 60.0

    # Renderiza a cena
    video = True
    if video:
        runtime.loop(n=4000, capture=np.arange(0, 4000, 40, dtype=np.int32))
        urenderer.utils.image_to_video(NOME_DA_CENA, fps=30)
        urenderer.utils.clear_workdir(NOME_DA_CENA, image_only=True)
    else:
        runtime.loop(capture=[1])
