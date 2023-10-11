# Copyright (c) OpenMMLab. All rights reserved.
from typing import Callable, Union

from agentlego.parsers import DefaultParser
from agentlego.schema import ToolMeta
from agentlego.types import AudioIO, ImageIO
from agentlego.utils import is_package_available, load_or_build_object, require
from ..base import BaseTool

if is_package_available('torch'):
    import torch


class AnythingToImage:

    @require(['diffusers', 'ftfy', 'iopath', 'timm'])
    def __init__(self, device):
        from diffusers import StableUnCLIPImg2ImgPipeline

        from .models.imagebind_model import imagebind_huge as ib

        pipe = load_or_build_object(
            StableUnCLIPImg2ImgPipeline.from_pretrained,
            pretrained_model_name_or_path='stabilityai/'
            'stable-diffusion-2-1-unclip',
            torch_dtype=torch.float16,
            variation='fp16')

        self.device = device
        self.pipe = pipe
        self.pipe.enable_model_cpu_offload()
        self.pipe.enable_vae_slicing()
        self.model = ib.imagebind_huge(pretrained=True)
        self.model.eval()


class AudioToImage(BaseTool):
    """A tool to generate image from an audio.

    Args:
        toolmeta (dict | ToolMeta): The meta info of the tool. Defaults to
            the :attr:`DEFAULT_TOOLMETA`.
        parser (Callable): The parser constructor, Defaults to
            :class:`DefaultParser`.
        device (str): The device to load the model. Defaults to 'cpu'.
    """
    DEFAULT_TOOLMETA = ToolMeta(
        name='Generate Image from Audio',
        description=('This tool can generate an image '
                     'according to the input audio'),
        inputs=['audio'],
        outputs=['image'],
    )

    @require(['diffusers', 'ftfy', 'iopath', 'timm'])
    def __init__(self,
                 toolmeta: Union[dict, ToolMeta] = DEFAULT_TOOLMETA,
                 parser: Callable = DefaultParser,
                 device: str = 'cpu'):
        super().__init__(toolmeta=toolmeta, parser=parser)
        self.device = device

    def setup(self):
        self._inferencer = load_or_build_object(
            AnythingToImage, device=self.device)

    def apply(self, audio: AudioIO) -> ImageIO:
        from .models.imagebind_model import imagebind_huge as ib

        audio_paths = [audio]
        audio_data = ib.load_and_transform_audio_data(audio_paths, self.device)
        embeddings = self._inferencer.model.forward(
            {ib.ModalityType.AUDIO: audio_data})
        embeddings = embeddings[ib.ModalityType.AUDIO]
        images = self._inferencer.pipe(
            image_embeds=embeddings.half(), width=512, height=512).images
        output_image = images[0]

        return ImageIO(output_image)


class ThermalToImage(BaseTool):
    """A tool to generate image from an thermal image.

    Args:
        toolmeta (dict | ToolMeta): The meta info of the tool. Defaults to
            the :attr:`DEFAULT_TOOLMETA`.
        parser (Callable): The parser constructor, Defaults to
            :class:`DefaultParser`.
        device (str): The device to load the model. Defaults to 'cpu'.
    """
    DEFAULT_TOOLMETA = ToolMeta(
        name='Generate Image from Thermal Image',
        description=('This tool can generate an image '
                     'according to the input thermal image.'),
        inputs=['image'],
        outputs=['image'],
    )

    @require(['diffusers', 'ftfy', 'iopath', 'timm'])
    def __init__(self,
                 toolmeta: Union[dict, ToolMeta] = DEFAULT_TOOLMETA,
                 parser: Callable = DefaultParser,
                 device: str = 'cpu'):
        super().__init__(toolmeta=toolmeta, parser=parser)
        self.device = device

    def setup(self):
        self._inferencer = load_or_build_object(
            AnythingToImage, device=self.device)

    def apply(self, thermal: ImageIO) -> ImageIO:
        from .models.imagebind_model import imagebind_huge as ib

        thermal_paths = [thermal]
        thermal_data = ib.load_and_transform_thermal_data(
            thermal_paths, self.device)
        embeddings = self._inferencer.model.forward(
            {ib.ModalityType.THERMAL: thermal_data})
        embeddings = embeddings[ib.ModalityType.THERMAL]
        images = self._inferencer.pipe(
            image_embeds=embeddings.half(), width=512, height=512).images
        output_image = images[0]

        return ImageIO(output_image)


class AudioImageToImage(BaseTool):
    """A tool to generate image from an audio and an image.

    Args:
        toolmeta (dict | ToolMeta): The meta info of the tool. Defaults to
            the :attr:`DEFAULT_TOOLMETA`.
        parser (Callable): The parser constructor, Defaults to
            :class:`DefaultParser`.
        device (str): The device to load the model. Defaults to 'cpu'.
    """
    DEFAULT_TOOLMETA = ToolMeta(
        name='Generate Image from Image and Audio',
        description=('This tool can generate an image according to '
                     'the input reference image and the input audio.'),
        inputs=['image', 'audio'],
        outputs=['image'],
    )

    @require(['diffusers', 'ftfy', 'iopath', 'timm'])
    def __init__(self,
                 toolmeta: Union[dict, ToolMeta] = DEFAULT_TOOLMETA,
                 parser: Callable = DefaultParser,
                 device: str = 'cpu'):
        super().__init__(toolmeta=toolmeta, parser=parser)
        self.device = device

    def setup(self):
        self._inferencer = load_or_build_object(
            AnythingToImage, device=self.device)

    def apply(self, image: ImageIO, audio: AudioIO) -> ImageIO:
        from .models.imagebind_model import imagebind_huge as ib

        # process image data
        vision_data = ib.load_and_transform_vision_data([image], self.device)
        embeddings = self._inferencer.model.forward(
            {ib.ModalityType.VISION: vision_data}, normalize=False)
        img_embeddings = embeddings[ib.ModalityType.VISION]

        # process audio data
        audio_data = ib.load_and_transform_audio_data([audio], self.device)
        embeddings = self._inferencer.model.forward({
            ib.ModalityType.AUDIO:
            audio_data,
        })
        audio_embeddings = embeddings[ib.ModalityType.AUDIO]

        embeddings = (img_embeddings + audio_embeddings) / 2
        images = self._inferencer.pipe(
            image_embeds=embeddings.half(), width=512, height=512).images
        output_image = images[0]

        return ImageIO(output_image)


class AudioTextToImage(BaseTool):
    """A tool to generate image from an audio and texts.

    Args:
        toolmeta (dict | ToolMeta): The meta info of the tool. Defaults to
            the :attr:`DEFAULT_TOOLMETA`.
        parser (Callable): The parser constructor, Defaults to
            :class:`DefaultParser`.
        device (str): The device to load the model. Defaults to 'cpu'.
    """
    DEFAULT_TOOLMETA = ToolMeta(
        name='Generate Image from Audio and Text',
        description=('This tool can generate an image according to '
                     'the input audio and the input description.'),
        inputs=['audio', 'text'],
        outputs=['image'],
    )

    @require(['diffusers', 'ftfy', 'iopath', 'timm'])
    def __init__(self,
                 toolmeta: Union[dict, ToolMeta] = DEFAULT_TOOLMETA,
                 parser: Callable = DefaultParser,
                 device: str = 'cpu'):
        super().__init__(toolmeta=toolmeta, parser=parser)
        self.device = device

    def setup(self):
        self._inferencer = load_or_build_object(
            AnythingToImage, device=self.device)

    def apply(self, audio: AudioIO, prompt: str) -> ImageIO:
        from .models.imagebind_model import imagebind_huge as ib

        audio_paths = [audio]
        text = ib.load_and_transform_text([prompt], self.device)
        embeddings = self._inferencer.model.forward(
            {ib.ModalityType.TEXT: text}, normalize=False)
        text_embeddings = embeddings[ib.ModalityType.TEXT]

        audio_data = ib.load_and_transform_audio_data(audio_paths, self.device)
        embeddings = self._inferencer.model.forward({
            ib.ModalityType.AUDIO:
            audio_data,
        })
        audio_embeddings = embeddings[ib.ModalityType.AUDIO]
        embeddings = text_embeddings * 0.5 + audio_embeddings * 0.5
        images = self._inferencer.pipe(
            image_embeds=embeddings.half(), width=512, height=512).images
        output_image = images[0]

        return ImageIO(output_image)
