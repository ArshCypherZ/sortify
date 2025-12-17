from src.infrastructure.embeddings.onnx_embedding import model_manager as onnx_manager

class ModelManagerProxy:
    def get_embedding_model(self):
        return onnx_manager

model_manager = ModelManagerProxy()
