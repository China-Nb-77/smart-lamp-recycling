export const installTypeLabelMap: Record<string, string> = {
  pendant: '吊灯',
  wall: '壁灯',
  floor: '落地灯',
  ceiling: '吸顶灯',
  desk: '台灯',
  any: '灯具',
};

export const materialLabelMap: Record<string, string> = {
  aluminum: '铝制',
  glass: '玻璃',
  brass: '铜制',
  any: '',
};

export const budgetLabelMap: Record<string, string> = {
  economy: '省钱优先',
  balanced: '预算均衡',
  premium: '升级款',
};

export const spaceLabelMap: Record<string, string> = {
  living_room: '客厅',
  dining_room: '餐厅',
  bedroom: '卧室',
  office: '书房',
  store: '门店',
};

export function getInstallTypeLabel(value?: string) {
  if (!value) {
    return '灯具';
  }
  return installTypeLabelMap[value] || value;
}

export function getMaterialLabel(value?: string) {
  if (!value) {
    return '';
  }
  return materialLabelMap[value] || value;
}

export function getBudgetLabel(value?: string) {
  if (!value) {
    return '';
  }
  return budgetLabelMap[value] || value;
}

export function getSpaceLabel(value?: string) {
  if (!value) {
    return '';
  }
  return spaceLabelMap[value] || value;
}

export function getLampDisplayTitle(input: {
  visual_style?: string;
  material?: string;
  fallbackTitle?: string;
}) {
  const styleLabel = getInstallTypeLabel(input.visual_style);
  const materialLabel = getMaterialLabel(input.material);
  if (materialLabel && styleLabel !== '灯具') {
    return `${materialLabel}${styleLabel}`;
  }
  if (styleLabel && styleLabel !== '灯具') {
    return styleLabel;
  }
  return input.fallbackTitle || '灯具';
}

export function getLampDisplaySubtitle(input: {
  visual_style?: string;
  material?: string;
  craft?: string;
}) {
  const parts = [getInstallTypeLabel(input.visual_style)];
  if (input.material) {
    parts.push(getMaterialLabel(input.material).replace(/制$/, '') || input.material);
  }
  if (input.craft) {
    parts.push(input.craft);
  }
  return parts.filter(Boolean).join(' · ');
}
