from fastapi import HTTPException, status


class ArcGISAuthenticationError(HTTPException):
    def __init__(self, detail: str = "ArcGIS authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class ArcGISUploadError(HTTPException):
    def __init__(self, detail: str = "Failed to upload to ArcGIS"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class FileProcessingError(HTTPException):
    def __init__(self, detail: str = "File processing failed"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )


class SPKNotFoundError(HTTPException):
    def __init__(self, spk: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No features found for SPK {spk}"
        )


class InvalidFileFormatError(HTTPException):
    def __init__(self, detail: str = "Invalid file format"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
