import cv2 as cv
import numpy as np
from OpenGL import GL
from OpenGL.constant import IntConstant


class Texture:
    '''
    Stores a texture for OpenGL rendering

    Usable for GL_TEXTURE_2D
    '''

    _default_parameters = {GL.GL_TEXTURE_WRAP_S: GL.GL_REPEAT,
                           GL.GL_TEXTURE_WRAP_T: GL.GL_REPEAT,
                           GL.GL_TEXTURE_MIN_FILTER: GL.GL_LINEAR,
                           GL.GL_TEXTURE_MAG_FILTER: GL.GL_LINEAR}

    def __init__(self, texture_data: np.ndarray,
                 data_format: IntConstant = GL.GL_RGB,
                 internal_format: IntConstant = GL.GL_RGB) -> None:
        '''
        Texture constructor

        Args:
            texture_data (np.ndarray): data of the texture
            data_format (IntConstant, optional): format of the texture data. Defaults to GL.GL_RGB.
            internal_format (IntConstant, optional): format to store the texture. Defaults to GL.GL_RGB.

        Raises:
            ValueError: if the texture dtype is not np.uint8
        '''

        if texture_data.dtype != np.uint8:
            raise ValueError(
                f"Only uint8 texture type is supported. texture_data is {texture_data.dtype}")

        self._data_format = data_format
        self._internal_format = internal_format

        ## SEU CÓDIGO AQUI ######################################################
        # Cria a textura
        texture_id = GL.glGenTextures(1)
        # Realiza o bind no contexto
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
        # Define os parâmetros da textura
        self.parameters: dict[IntConstant, int] = {}
        for parameter, value in Texture._default_parameters.items():
            GL.glTexParameteri(GL.GL_TEXTURE_2D, parameter, value)
            self.parameters[parameter] = value
        
        height, width = texture_data.shape[0], texture_data.shape[1]
        # Especifica os dados da textura
        GL.glTexImage2D(
            GL.GL_TEXTURE_2D,
            0,                           # Nível de Mipmap base
            self._internal_format,        # Formato interno na GPU
            width,
            height,
            0,                           # Borda (sempre mantenho 0)
            self._data_format,            # Formato dos dados no NumPy
            GL.GL_UNSIGNED_BYTE,         # Tipo do dado (uint8)
            texture_data                 # O array de pixels
        )
        # Gera os mipmaps da textura
        GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
        #########################################################################

        self._texture_id = texture_id

    def bind_at_unit(self, unit: int) -> None:
        '''
        Binds the texture to a texture unit

        Args:
            unit (int): unit to bind
        '''
        ## SEU CÓDIGO AQUI ######################################################
        # Ativa a texture unit e realiza o bind da textura
        # OBS: cada texture unit é sequencial: GL.GL_TEXTURE1 = GL.GL_TEXTURE0+1
        GL.glActiveTexture(GL.GL_TEXTURE0 + unit)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture_id)
        #########################################################################


    def set_parameter(self, parameter: IntConstant, value: int):
        '''
        Set a texture parameter

        Args:
            parameter (IntConstant): parameter to set
            value (int): value to set
        '''
        if (parameter not in self.parameters) or self.parameters[parameter] != value:
            GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture_id)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, parameter, value)

            self.parameters[parameter] = value

    @classmethod
    def load_file(cls,
                  path: str,
                  drop_alpha: bool = False,
                  srgb: bool = False) -> "Texture":
        '''
        Load a texture from a image file

        Args:
            path (str): file path
            drop_alpha (bool, optional): is should drop the texture alpha. Defaults to False.

        Returns:
            Texture: loaded texture
        '''
        texture_data = cv.imread(path, cv.IMREAD_UNCHANGED)

        texture_data = np.flipud(texture_data)

        if texture_data.ndim == 2:
            data_format = GL.GL_RED
            internal_format = GL.GL_R8

        elif texture_data.shape[-1] == 3:
            data_format = GL.GL_BGR

            if srgb:
                internal_format = GL.GL_SRGB
            else:
                internal_format = GL.GL_RGB
        elif drop_alpha:
            data_format = GL.GL_BGRA

            if srgb:
                internal_format = GL.GL_SRGB
            else:
                internal_format = GL.GL_RGB
        else:
            data_format = GL.GL_BGRA

            if srgb:
                internal_format = GL.GL_SRGBA
            else:
                internal_format = GL.GL_RGBA

        return Texture(texture_data, data_format, internal_format)
