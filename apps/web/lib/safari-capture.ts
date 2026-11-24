export const safariCaptureEnabled = process.env.NEXT_PUBLIC_STUDIO_SAFARI_CAPTURE === "1" ||
  (process.env.NEXT_PUBLIC_STUDIO_SAFARI_CAPTURE !== "0" && process.env.NODE_ENV === "development");
