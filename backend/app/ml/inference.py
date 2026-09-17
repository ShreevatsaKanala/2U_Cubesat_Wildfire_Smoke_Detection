"""
Abstract base class for ML inference engines.

Defines the interface that all ML classifiers must implement.
Future implementations will include TensorFlow, ONNX, and TensorRT
backends for actual smoke detection models.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class InferenceEngine(ABC):
    """
    Abstract base class for ML inference engines.

    All concrete inference implementations must implement the classify
    method and provide model information. This interface ensures
    compatibility with the observation pipeline.
    """

    @abstractmethod
    def classify(self, image_path: str) -> Dict[str, Any]:
        """
        Classify an image for smoke and wildfire detection.

        Args:
            image_path: Path to the image file to classify

        Returns:
            Dictionary containing:
                - smoke_probability (float): 0-1, probability of smoke
                - wildfire_probability (float): 0-1, probability of wildfire
                - confidence (float): 0-1, model confidence in prediction
                - model_name (str): Name of the model used
                - model_version (str): Version of the model
                - inference_latency_ms (float): Time taken for inference
                - processing_status (str): Status of processing
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary containing:
                - name (str): Model name
                - version (str): Model version
                - input_shape (list): Expected input shape [height, width, channels]
                - output_shape (list): Output shape
                - framework (str): ML framework used
                - device (str): Compute device (CPU/GPU)
        """
        pass

    def get_supported_classes(self) -> list:
        """
        Get list of supported detection classes.

        Returns:
            List of class names this model can detect
        """
        return ["smoke", "wildfire", "clear"]

    def warmup(self, num_iterations: int = 5) -> None:
        """
        Warm up the model with dummy predictions.

        Args:
            num_iterations: Number of warmup iterations
        """
        pass
