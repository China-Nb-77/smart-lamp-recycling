function locateWithOptions(options: PositionOptions): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, options);
  });
}

export async function getCurrentPositionWithFallback() {
  if (!navigator.geolocation) {
    throw new Error('当前浏览器不支持定位');
  }

  try {
    return await locateWithOptions({
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    });
  } catch {
    return locateWithOptions({
      enableHighAccuracy: false,
      timeout: 15000,
      maximumAge: 120000,
    });
  }
}
