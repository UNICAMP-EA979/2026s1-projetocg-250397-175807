import ctypes
from concurrent.futures import ProcessPoolExecutor
from typing import TYPE_CHECKING, Any, TypeAlias, cast

import cv2 as cv
import glfw
import numpy as np
from OpenGL import GL

from urenderer.geometry.mesh import Mesh
from urenderer.node import Camera, Light, Node
from urenderer.renderer.renderer import Renderer
from urenderer.utils import get_filename_unique

from .material import Material

if TYPE_CHECKING:
    GLFWWindow = Any
else:
    GLFWWindow = ctypes.POINTER(glfw._GLFWwindow)


def save_frame(path: str, frame: np.ndarray) -> None:
    '''
    Save a frame

    Args:
        path (str): path to save
        frame (np.ndarray): frame
    '''
    cv.imwrite(path, frame)


class OpenGLRenderer(Renderer):
    '''
    Renderer using OpenGL
    '''

    def __init__(self, screen_width: int, screen_height: int) -> None:
        '''
        OpenGLRenderer initializer.

        Args:
            screen_width (int): screen width
            screen_height (int): screen height
            show (bool, optional): if should show the rendered frame. Defaults to True.
        '''
        super().__init__(screen_width, screen_height)
        self._executor = ProcessPoolExecutor(max_workers=1)

        ## SEU CÓDIGO AQUI ######################################################
        # Inicializa o GLFW, core profile e OpenGL 3.3
        if not glfw.init():
            raise RuntimeError("Falha ao inicializar a biblioteca GLFW")
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL.GL_TRUE)
        #########################################################################

        ## SEU CÓDIGO AQUI ######################################################
        # Cria a janela, associando ela ao contexto
        # e configurando o tamanho dela no OpenGl
        window = glfw.create_window(self.screen_width, self.screen_height, "EA979 - Hello Cube", None, None)
        if not window:
            glfw.terminate()
            raise RuntimeError("Falha ao criar a janela GLFW")
            
        glfw.make_context_current(window)
        GL.glViewport(0, 0, self.screen_width, self.screen_height)
        #########################################################################

        ## SEU CÓDIGO AQUI ######################################################
        # Habilite o uso de GL_FRAMEBUFFER_SRGB para convertor cores para sRGB
        GL.glEnable(GL.GL_FRAMEBUFFER_SRGB)
        #########################################################################

        glfw.set_framebuffer_size_callback(
            window, self._framebuffer_size_callback)

        GL.glEnable(GL.GL_DEPTH_TEST)

        self._window = cast(GLFWWindow, window)
        self.background_color = np.array([1.0, 0.0, 1.0, 1.0])

        self.ambient_color = np.array([0.0, 0.0, 0.0], dtype=np.float32)

        GL.glDisable(GL.GL_DITHER)

    def _framebuffer_size_callback(self, window: GLFWWindow,
                                   width: int, height: int):
        '''
        Callback for a change in the framebuffer size

        Args:
            window (GLFWWindow): window with size change
            width (int): new width
            height (int): new heigth
        '''
        GL.glViewport(0, 0, width, height)

    def start(self, camera: Camera, view_matrix: np.ndarray, name: str) -> None:
        '''
        Start the frame rendering

        Args:
            camera (Camera): current camera.
            view_matrix (np.ndarray): camera view matrix.
            name (str): name of the application
        '''
        super().start(camera, view_matrix, name)
        self._view_matrix = view_matrix
        self._projection_matrix = camera.projection_matrix
        self._name = name
        self._lights: list[dict[str, Light | np.ndarray]] = []

        glfw.set_window_title(self._window, name)

        ## SEU CÓDIGO AQUI ######################################################
        # Limpe os buffers de cor e profundidade (COLOR_BUFFER e DEPTH_BUFFER)
        # Para o de cor, utilize a cor self.background_color
        GL.glClearColor(self.background_color[0], self.background_color[1], 
                        self.background_color[2], self.background_color[3])
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        #########################################################################

    def validate(self, node: Node, model_transformation: np.ndarray) -> bool:
        '''
        Validate a node for rendering.

        Check if the node is compatible to be rendered with this renderer.

        Args:
            node (Node): node to validate.

        Returns:
            bool: True if the node is valid
        '''
        if isinstance(node, Light):
            dummy = np.zeros(4)
            dummy[-1] = 1
            position = model_transformation@dummy
            position = position[:3].astype(np.float32)

            self._lights.append(
                {"node": node, "position": position})
        return ("material" in node.render_data and
                "mesh" in node.render_data)

    def render_valid_node(self, node: Node, model_transformation: np.ndarray):
        '''
        Renders a validated node

        Args:
            node (Node): node to render
            model_transformation (np.ndarray): node model transformation in the scene
        '''
        material: Material = node.render_data["material"]
        mesh: Mesh = node.render_data["mesh"]

        material.use()

        ## SEU CÓDIGO AQUI ######################################################
        # Defina as uniforms 'modelTransformation', 'viewTransformation' e
        # 'projectionMatrix' do material.shader, as matrizes de transformação de
        # coordenadas 4x4.
        #
        # Utilize o método set_uniform do shader, pois não queremos alterar a
        # uniform para todo uso do material.
        #
        # Atente-se que os valores precisam ser convertidos para np.float32
        material.use()
        
        material.shader.set_uniform("modelTransformation", model_transformation.astype(np.float32))
        material.shader.set_uniform("viewTransformation", self._view_matrix.astype(np.float32))
        material.shader.set_uniform("projectionMatrix", self._projection_matrix.astype(np.float32))
        #########################################################################

        ## SEU CÓDIGO AQUI ######################################################
        # Defina a uniform lights para os valores correspondetes de cada luz.
        #
        # As luzes precisam ser enviadas sequencialmente ([luz0, luz1, UNDEFINED, UNDEFINED, ...])
        # Você pode alterar o valor da uniforme 'type' da light 0 usando: 'light[0].type'.
        #
        # Utilize o método set_uniform do shader

        # Preenche tipo, posição, cor e intensidade de cada um
        max_lights = 10  # Limite máximo de 10 por causa 01-fragment.fs

        for i, light_info in enumerate(self._lights):
            if i >= max_lights:
                break
            light = cast(Light, light_info["node"])
            light_position = cast(np.ndarray, light_info["position"])

            # Tipo da luz
            material.shader.set_uniform(f"lights[{i}].type", int(light.light_type.value))

            # Cor e intensidade
            material.shader.set_uniform(f"lights[{i}].color", light.light_color.astype(np.float32))
            material.shader.set_uniform(f"lights[{i}].intensity", float(light.light_intensity))

            # Direção
            material.shader.set_uniform(f"lights[{i}].direction", light.light_direction.astype(np.float32))

            # Posição e Distância de referência (para luzes pontuais)
            material.shader.set_uniform(f"lights[{i}].position", light_position.astype(np.float32))
            material.shader.set_uniform(f"lights[{i}].reference_distance", float(light.light_reference_distance))

        # Extrai a posição da câmera no espaço do mundo a partir da matriz de View inversa
        view_inv = np.linalg.inv(self._view_matrix)
        camera_pos = view_inv[:3, 3].astype(np.float32)
        
        # Envia para o shader atual
        material.shader.set_uniform("cameraPosition", camera_pos)

        # Desativa os slots de luz restantes que não estão na cena
        for i in range(len(self._lights), max_lights):
            material.shader.set_uniform(f"lights[{i}].type", 0)
        #########################################################################

        ## SEU CÓDIGO AQUI ######################################################
        # Defina a uniform ambientColor para self.ambient_color
        #
        # Utilize o método set_uniform do shader
        material.shader.set_uniform("ambientColor", self.ambient_color.astype(np.float32))
        #########################################################################

        mesh.draw()

    def end(self, capture: bool = False):
        '''
        Ends the frame rendering

        Args:
            capture (bool, optional): if should save the current frame. Defaults to False.
        '''
        super().end(capture)

        if capture:
            GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)

            frame_data = GL.glReadPixels(0,  # first pixel x
                                         0,  # first pixel y
                                         self.screen_width,  # dimensão do retângulo sendo lido
                                         self.screen_height,  # dimensão do retângulo sendo lido
                                         GL.GL_BGRA,
                                         GL.GL_UNSIGNED_BYTE)
            frame_data = cast(bytes, frame_data)

            frame = np.frombuffer(frame_data, np.uint8)
            frame = frame.reshape([self.screen_height, self.screen_width, 4])
            frame = np.flipud(frame)

            filename = get_filename_unique(self._name)

            self._executor.submit(save_frame, filename, frame)

        ## SEU CÓDIGO AQUI ######################################################
        # Troque o buffer frontal e traseiro, mostrando o novo buffer renderizado
        glfw.swap_buffers(self._window)
        #########################################################################

        glfw.poll_events()

    def should_stop(self) -> bool:
        return glfw.window_should_close(self._window)

    def __del__(self):
        self._executor.shutdown()
        glfw.terminate()
