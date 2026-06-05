type UploadedImageCardProps = {
  imageUrl: string;
  alt: string;
};

export function UploadedImageCard({ imageUrl, alt }: UploadedImageCardProps) {
  return (
    <div className="uploaded-image-card">
      <img src={imageUrl} alt={alt} className="uploaded-image-card__image" />
    </div>
  );
}
