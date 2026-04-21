import { useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Check, ChevronDown, ChevronRight, Circle, LocateFixed, Minus, Plus, Store, X } from 'lucide-react';
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import type { VisionRecommendation, VisionRecommendationResponse } from '../../../types/vision';
import { buildVisionImageUrl } from '../../../services/visionApi';
import { paymentApi } from '../../../services/paymentApi';
import { getCurrentPositionWithFallback } from '../../payment/geolocation';
import { getBudgetLabel, getInstallTypeLabel, getSpaceLabel } from '../display';

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

type ReplacementRecommendationsCardProps = {
  payload: VisionRecommendationResponse;
  onSelect?: (
    sessionId: string,
    skuId: string,
    options?: {
      selected_new_title?: string;
      selected_new_image_path?: string;
      selected_new_kind?: string;
      qty?: number;
      selection_summary?: string;
      name?: string;
      phone?: string;
      full_address?: string;
      street?: string;
      longitude?: number;
      latitude?: number;
    },
  ) => void;
};

type AddressEntry = {
  id: string;
  fullAddress: string;
  detailAddress: string;
  contactName: string;
  contactPhone: string;
  tag: string;
  latitude: number;
  longitude: number;
};

type ProductSelection = {
  spec: string;
  colorTemp: string;
  finish: string;
  qty: number;
  confirmed: boolean;
};

type AddressFormState = {
  fullAddress: string;
  detailAddress: string;
  contactName: string;
  contactPhone: string;
  tag: string;
  latitude: number;
  longitude: number;
};

const defaultCenter: [number, number] = [31.2304, 121.4737];
const defaultColorTemps = ['暖白 3000K', '中性光 4000K', '冷白 6000K'];
const defaultAddressTags = ['家', '公司', '学校', '项目', '门店'];

function createAddressId() {
  return `addr_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function buildDefaultSelection(item: VisionRecommendation): ProductSelection {
  const spec = item.size_band || '标准款';
  const finish = item.material ? getInstallTypeLabel(item.material) || item.material : '哑光';
  return {
    spec,
    colorTemp: defaultColorTemps[1],
    finish,
    qty: 1,
    confirmed: false,
  };
}

function clampQty(value: number) {
  return Math.max(1, Math.min(99, Math.round(value)));
}

function mapAddressToEntry(
  source: {
    full_address?: string;
    street?: string;
    latitude?: number;
    longitude?: number;
  },
  fallbackName = '联系人',
): AddressEntry {
  return {
    id: createAddressId(),
    fullAddress: source.full_address || source.street || '请补充收货地址',
    detailAddress: source.street || '',
    contactName: fallbackName,
    contactPhone: '13800000000',
    tag: '学校',
    latitude: Number(source.latitude || defaultCenter[0]),
    longitude: Number(source.longitude || defaultCenter[1]),
  };
}

function formatSelectionSummary(selection: ProductSelection) {
  return `${selection.spec} / ${selection.colorTemp} / ${selection.finish} / x${selection.qty}`;
}

function buildStoreProducts(payload: VisionRecommendationResponse) {
  const categories = ['猜你喜欢', '新品专区', '风格灯具', '经典系列', '材质精选'];
  const products = payload.recommendations.flatMap((item, index) => {
    return [
      {
        id: `${item.sku_id}_main`,
        name: item.title,
        subtitle: `${getInstallTypeLabel(item.visual_style)} · ${item.craft || '工艺款'}`,
        price: item.base_price,
        imagePath: item.image_path,
        category: categories[index % categories.length],
        recommendation: item,
      },
      {
        id: `${item.sku_id}_variant`,
        name: `${item.title}（升级版）`,
        subtitle: `${getInstallTypeLabel(item.visual_style)} · ${item.material || '复合材质'}`,
        price: Math.max(item.base_price + 80, item.base_price),
        imagePath: item.image_path,
        category: categories[(index + 1) % categories.length],
        recommendation: item,
      },
    ];
  });
  return {
    categories,
    products,
  };
}

function AddressMapMarker({
  position,
  onChange,
}: {
  position: [number, number];
  onChange: (next: [number, number]) => void;
}) {
  useMapEvents({
    click(event) {
      onChange([event.latlng.lat, event.latlng.lng]);
    },
  });
  return <Marker position={position} />;
}

function MapViewportSync({ position }: { position: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(position);
  }, [map, position]);
  return null;
}

export function ReplacementRecommendationsCard({
  payload,
  onSelect,
}: ReplacementRecommendationsCardProps) {
  const carouselRef = useRef<HTMLDivElement | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [addresses, setAddresses] = useState<AddressEntry[]>([]);
  const [selectedAddressId, setSelectedAddressId] = useState('');
  const [addressSheetOpen, setAddressSheetOpen] = useState(false);
  const [addAddressSheetOpen, setAddAddressSheetOpen] = useState(false);
  const [detailSheetOpen, setDetailSheetOpen] = useState(false);
  const [storeSheetOpen, setStoreSheetOpen] = useState(false);
  const [mapLocating, setMapLocating] = useState(false);
  const [sheetError, setSheetError] = useState<string | null>(null);
  const [detailSkuId, setDetailSkuId] = useState('');
  const [selectionBySku, setSelectionBySku] = useState<Record<string, ProductSelection>>({});
  const [addressForm, setAddressForm] = useState<AddressFormState>({
    fullAddress: '',
    detailAddress: '',
    contactName: '赵先生',
    contactPhone: '13800000000',
    tag: '学校',
    latitude: defaultCenter[0],
    longitude: defaultCenter[1],
  });
  const storeData = useMemo(() => buildStoreProducts(payload), [payload]);

  const selectedAddress =
    addresses.find((item) => item.id === selectedAddressId) || addresses[0] || null;
  const detailRecommendation = payload.recommendations.find((item) => item.sku_id === detailSkuId) || null;

  useEffect(() => {
    if (!payload.recommendations.length) {
      return;
    }
    setSelectionBySku((current) => {
      const next = { ...current };
      payload.recommendations.forEach((item) => {
        if (!next[item.sku_id]) {
          next[item.sku_id] = buildDefaultSelection(item);
        }
      });
      return next;
    });
  }, [payload.recommendations]);

  useEffect(() => {
    if (activeIndex <= payload.recommendations.length - 1) {
      return;
    }
    setActiveIndex(0);
  }, [activeIndex, payload.recommendations.length]);

  useEffect(() => {
    let disposed = false;
    async function bootstrapAddress() {
      try {
        const position = await getCurrentPositionWithFallback();
        const normalized = await paymentApi.locateAddress(
          position.coords.latitude,
          position.coords.longitude,
          '',
        );
        if (disposed) {
          return;
        }
        const entry = mapAddressToEntry(normalized, '赵先生');
        setAddresses([entry]);
        setSelectedAddressId(entry.id);
        setAddressForm((current) => ({
          ...current,
          fullAddress: normalized.full_address || current.fullAddress,
          detailAddress: normalized.street || current.detailAddress,
          latitude: normalized.latitude || current.latitude,
          longitude: normalized.longitude || current.longitude,
        }));
      } catch {
        if (disposed) {
          return;
        }
        const fallback = mapAddressToEntry(
          {
            full_address: '请点击修改，补充收货地址',
            latitude: defaultCenter[0],
            longitude: defaultCenter[1],
          },
          '赵先生',
        );
        setAddresses([fallback]);
        setSelectedAddressId(fallback.id);
      }
    }
    void bootstrapAddress();
    return () => {
      disposed = true;
    };
  }, []);

  useEffect(() => {
    const carousel = carouselRef.current;
    if (!carousel) {
      return;
    }
    const onScroll = () => {
      const cards = Array.from(
        carousel.querySelectorAll<HTMLElement>('.lamp-commerce-card'),
      );
      if (!cards.length) {
        return;
      }
      const center = carousel.scrollLeft + carousel.clientWidth / 2;
      let nearest = 0;
      let nearestDistance = Number.POSITIVE_INFINITY;
      cards.forEach((card, index) => {
        const cardCenter = card.offsetLeft + card.offsetWidth / 2;
        const distance = Math.abs(cardCenter - center);
        if (distance < nearestDistance) {
          nearest = index;
          nearestDistance = distance;
        }
      });
      setActiveIndex(nearest);
    };
    carousel.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      carousel.removeEventListener('scroll', onScroll);
    };
  }, []);

  const confirmedItems = useMemo(
    () => Object.entries(selectionBySku).filter(([, value]) => value.confirmed),
    [selectionBySku],
  );

  const storeTotal = useMemo(() => {
    return confirmedItems.reduce((sum, [sku, selection]) => {
      const matched = payload.recommendations.find((item) => item.sku_id === sku);
      return sum + (matched ? matched.base_price * selection.qty : 0);
    }, 0);
  }, [confirmedItems, payload.recommendations]);

  function getSelection(skuId: string) {
    const recommendation = payload.recommendations.find((item) => item.sku_id === skuId);
    if (!recommendation) {
      return buildDefaultSelection({
        sku_id: skuId,
        title: '',
        visual_style: 'any',
        material: '',
        size_band: '标准款',
        craft: '',
        base_price: 0,
        fit_score: 0,
        recommendation_reasons: [],
      });
    }
    return selectionBySku[skuId] || buildDefaultSelection(recommendation);
  }

  function updateSelection(
    skuId: string,
    updater: (current: ProductSelection) => ProductSelection,
  ) {
    setSelectionBySku((current) => {
      const baseline = getSelection(skuId);
      return {
        ...current,
        [skuId]: updater(baseline),
      };
    });
  }

  function openDetailSheet(skuId: string) {
    setDetailSkuId(skuId);
    setDetailSheetOpen(true);
    setSheetError(null);
  }

  async function handleLocateForAddressForm() {
    setMapLocating(true);
    setSheetError(null);
    try {
      const position = await getCurrentPositionWithFallback();
      const normalized = await paymentApi.locateAddress(
        position.coords.latitude,
        position.coords.longitude,
        addressForm.fullAddress,
      );
      setAddressForm((current) => ({
        ...current,
        fullAddress: normalized.full_address || current.fullAddress,
        detailAddress: normalized.street || current.detailAddress,
        latitude: normalized.latitude || current.latitude,
        longitude: normalized.longitude || current.longitude,
      }));
    } catch (error) {
      setSheetError(error instanceof Error ? error.message : '定位失败，请手动输入地址');
    } finally {
      setMapLocating(false);
    }
  }

  async function handleSaveAddress(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSheetError(null);
    try {
      const normalized = await paymentApi.normalizeAddress({
        full_address: addressForm.fullAddress,
        street: addressForm.detailAddress,
        latitude: addressForm.latitude,
        longitude: addressForm.longitude,
      });
      const entry: AddressEntry = {
        id: createAddressId(),
        fullAddress: normalized.full_address || addressForm.fullAddress,
        detailAddress: addressForm.detailAddress,
        contactName: addressForm.contactName,
        contactPhone: addressForm.contactPhone,
        tag: addressForm.tag,
        latitude: addressForm.latitude,
        longitude: addressForm.longitude,
      };
      setAddresses((current) => [entry, ...current]);
      setSelectedAddressId(entry.id);
      setAddAddressSheetOpen(false);
      setAddressSheetOpen(true);
    } catch (error) {
      setSheetError(error instanceof Error ? error.message : '保存地址失败，请稍后重试');
    }
  }

  function handleConfirmLampSelection() {
    if (!detailRecommendation) {
      return;
    }
    const selection = getSelection(detailRecommendation.sku_id);
    updateSelection(detailRecommendation.sku_id, (current) => ({
      ...current,
      confirmed: true,
    }));
    setDetailSheetOpen(false);
    if (payload.session_id && onSelect) {
      onSelect(payload.session_id, detailRecommendation.sku_id, {
        selected_new_title: detailRecommendation.title,
        selected_new_image_path: detailRecommendation.image_path,
        selected_new_kind: detailRecommendation.visual_style,
        qty: selection.qty,
        selection_summary: formatSelectionSummary(selection),
        name: selectedAddress?.contactName,
        phone: selectedAddress?.contactPhone,
        full_address: selectedAddress?.fullAddress,
        street: selectedAddress?.detailAddress,
        longitude: selectedAddress?.longitude,
        latitude: selectedAddress?.latitude,
      });
    }
  }

  function renderSelectionDots() {
    return (
      <div className="lamp-commerce-dots" aria-hidden="true">
        {payload.recommendations.map((item, index) => (
          <i
            key={item.sku_id}
            className={index === activeIndex ? 'lamp-commerce-dot lamp-commerce-dot--active' : 'lamp-commerce-dot'}
          />
        ))}
      </div>
    );
  }

  return (
    <article className="biz-card biz-card--vision lamp-commerce">
      <div className="biz-card__head lamp-commerce__head">
        <div>
          <strong>智能选灯助手</strong>
          <p>
            当前你的地址是
            <button
              type="button"
              className="lamp-commerce__address-link"
              onClick={() => setAddressSheetOpen(true)}
            >
              {selectedAddress?.fullAddress || '请点击补充收货地址'}（点击修改）
            </button>
          </p>
          <p className="lamp-commerce__intro">
            基于回收识别结果，已按
            {getSpaceLabel(payload.space) || '安装空间'}
            /
            {getBudgetLabel(payload.preferences.budget_level) || '预算均衡'}
            /
            {getInstallTypeLabel(payload.preferences.install_type) || '灯具'}
            为你推荐可替换灯具。
          </p>
        </div>
      </div>

      <div className="lamp-commerce-carousel" ref={carouselRef}>
        {payload.recommendations.map((item) => {
          const selection = getSelection(item.sku_id);
          return (
            <section key={item.sku_id} className="lamp-commerce-card">
              <header className="lamp-commerce-card__meta">
                <span>灯具旗舰店 · 评分 {item.fit_score.toFixed(1)} · 约45分钟</span>
                <span>{item.size_band || '标准款'}</span>
              </header>
              <h3>{item.title}</h3>
              <p>{item.recommendation_reasons[0] || '已根据你的旧灯类型自动匹配。'}</p>
              {item.image_path ? (
                <img src={buildVisionImageUrl(item.image_path)} alt={item.title} className="lamp-commerce-card__image" />
              ) : (
                <div className="lamp-commerce-card__image lamp-commerce-card__image--empty">暂无图片</div>
              )}
              <div className="lamp-commerce-card__selection">{formatSelectionSummary(selection)}</div>
              <footer className="lamp-commerce-card__footer">
                <strong>￥{item.base_price.toFixed(0)}</strong>
                <button
                  type="button"
                  className="secondary-button lamp-commerce-card__store-btn"
                  onClick={() => {
                    setStoreSheetOpen(true);
                    setDetailSkuId(item.sku_id);
                  }}
                >
                  <Store size={14} />
                  进店选购
                </button>
              </footer>
              <button
                type="button"
                className="primary-button lamp-commerce-card__choose-btn"
                onClick={() => openDetailSheet(item.sku_id)}
              >
                选这个
              </button>
            </section>
          );
        })}
      </div>
      {renderSelectionDots()}

      {addressSheetOpen ? (
        <div className="sheet-backdrop lamp-sheet-backdrop" onClick={() => setAddressSheetOpen(false)}>
          <section className="sheet-panel lamp-sheet lamp-sheet--address" onClick={(event) => event.stopPropagation()}>
            <header className="lamp-sheet__header">
              <strong>选择收货地址</strong>
              <button type="button" className="icon-button" onClick={() => setAddressSheetOpen(false)}>
                <X size={18} />
              </button>
            </header>
            <div className="lamp-address-list">
              {addresses.map((address) => (
                <button
                  type="button"
                  key={address.id}
                  className={`lamp-address-card ${selectedAddressId === address.id ? 'lamp-address-card--active' : ''}`}
                  onClick={() => setSelectedAddressId(address.id)}
                >
                  <span className="lamp-address-card__radio">
                    {selectedAddressId === address.id ? <Check size={14} /> : <Circle size={14} />}
                  </span>
                  <div className="lamp-address-card__content">
                    <strong>{address.fullAddress}</strong>
                    <p>
                      <span>{address.tag}</span>
                      {address.contactName} {address.contactPhone}
                    </p>
                  </div>
                  <ChevronRight size={16} />
                </button>
              ))}
            </div>
            <button
              type="button"
              className="primary-button lamp-sheet__footer-btn"
              onClick={() => {
                setAddressSheetOpen(false);
                setAddAddressSheetOpen(true);
              }}
            >
              新增收货地址
            </button>
          </section>
        </div>
      ) : null}

      {addAddressSheetOpen ? (
        <div className="sheet-backdrop lamp-sheet-backdrop" onClick={() => setAddAddressSheetOpen(false)}>
          <section className="sheet-panel lamp-sheet lamp-sheet--add-address" onClick={(event) => event.stopPropagation()}>
            <header className="lamp-sheet__header">
              <strong>新增收货地址</strong>
              <button type="button" className="icon-button" onClick={() => setAddAddressSheetOpen(false)}>
                <X size={18} />
              </button>
            </header>
            <div className="lamp-map-wrap">
              <MapContainer center={[addressForm.latitude, addressForm.longitude]} zoom={16} scrollWheelZoom={false}>
                <MapViewportSync position={[addressForm.latitude, addressForm.longitude]} />
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <AddressMapMarker
                  position={[addressForm.latitude, addressForm.longitude]}
                  onChange={(next) => {
                    setAddressForm((current) => ({
                      ...current,
                      latitude: next[0],
                      longitude: next[1],
                    }));
                  }}
                />
              </MapContainer>
              <button
                type="button"
                className="secondary-button lamp-map-wrap__locate"
                onClick={() => {
                  void handleLocateForAddressForm();
                }}
                disabled={mapLocating}
              >
                <LocateFixed size={15} />
                {mapLocating ? '定位中' : '使用当前位置'}
              </button>
            </div>
            <form className="lamp-address-form" onSubmit={(event) => void handleSaveAddress(event)}>
              <label>
                <span>地址</span>
                <input
                  value={addressForm.fullAddress}
                  onChange={(event) =>
                    setAddressForm((current) => ({ ...current, fullAddress: event.target.value }))
                  }
                  placeholder="选择收货地址"
                  required
                />
              </label>
              <label>
                <span>门牌号</span>
                <input
                  value={addressForm.detailAddress}
                  onChange={(event) =>
                    setAddressForm((current) => ({ ...current, detailAddress: event.target.value }))
                  }
                  placeholder="例如：A座1201"
                  required
                />
              </label>
              <label>
                <span>收货人</span>
                <input
                  value={addressForm.contactName}
                  onChange={(event) =>
                    setAddressForm((current) => ({ ...current, contactName: event.target.value }))
                  }
                  placeholder="填写收货人姓名"
                  required
                />
              </label>
              <label>
                <span>手机号</span>
                <input
                  value={addressForm.contactPhone}
                  onChange={(event) =>
                    setAddressForm((current) => ({ ...current, contactPhone: event.target.value }))
                  }
                  placeholder="填写手机号"
                  required
                />
              </label>
              <div className="lamp-address-tags">
                {defaultAddressTags.map((tag) => (
                  <button
                    type="button"
                    key={tag}
                    className={addressForm.tag === tag ? 'lamp-chip lamp-chip--active' : 'lamp-chip'}
                    onClick={() => setAddressForm((current) => ({ ...current, tag }))}
                  >
                    {tag}
                  </button>
                ))}
              </div>
              {sheetError ? <p className="lamp-sheet__error">{sheetError}</p> : null}
              <button type="submit" className="primary-button lamp-sheet__footer-btn">
                保存
              </button>
            </form>
          </section>
        </div>
      ) : null}

      {detailSheetOpen && detailRecommendation ? (
        <div className="sheet-backdrop lamp-sheet-backdrop" onClick={() => setDetailSheetOpen(false)}>
          <section className="sheet-panel lamp-sheet lamp-sheet--detail" onClick={(event) => event.stopPropagation()}>
            <header className="lamp-sheet__header">
              <div>
                <strong>{detailRecommendation.title}</strong>
                <p>已选：{formatSelectionSummary(getSelection(detailRecommendation.sku_id))}</p>
              </div>
              <button type="button" className="icon-button" onClick={() => setDetailSheetOpen(false)}>
                <ChevronDown size={18} />
              </button>
            </header>
            <div className="lamp-detail-head">
              {detailRecommendation.image_path ? (
                <img src={buildVisionImageUrl(detailRecommendation.image_path)} alt={detailRecommendation.title} />
              ) : (
                <div className="lamp-detail-head__placeholder">暂无图片</div>
              )}
              <div>
                <h4>{detailRecommendation.title}</h4>
                <p>
                  {getInstallTypeLabel(detailRecommendation.visual_style)} · {detailRecommendation.material || '标准材质'}
                </p>
                <strong>￥{detailRecommendation.base_price.toFixed(0)}</strong>
              </div>
            </div>
            <section className="lamp-option-group">
              <h5>规格</h5>
              <div className="lamp-option-grid">
                {['紧凑款', detailRecommendation.size_band || '标准款', '加宽款'].map((spec) => (
                  <button
                    key={spec}
                    type="button"
                    className={getSelection(detailRecommendation.sku_id).spec === spec ? 'lamp-chip lamp-chip--active' : 'lamp-chip'}
                    onClick={() =>
                      updateSelection(detailRecommendation.sku_id, (current) => ({
                        ...current,
                        spec,
                      }))
                    }
                  >
                    {spec}
                  </button>
                ))}
              </div>
            </section>
            <section className="lamp-option-group">
              <h5>色温</h5>
              <div className="lamp-option-grid">
                {defaultColorTemps.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={getSelection(detailRecommendation.sku_id).colorTemp === option ? 'lamp-chip lamp-chip--active' : 'lamp-chip'}
                    onClick={() =>
                      updateSelection(detailRecommendation.sku_id, (current) => ({
                        ...current,
                        colorTemp: option,
                      }))
                    }
                  >
                    {option}
                  </button>
                ))}
              </div>
            </section>
            <section className="lamp-option-group">
              <h5>材质工艺</h5>
              <div className="lamp-option-grid">
                {[detailRecommendation.material || '哑光', '金属拉丝', '玻璃罩'].map((finish) => (
                  <button
                    key={finish}
                    type="button"
                    className={getSelection(detailRecommendation.sku_id).finish === finish ? 'lamp-chip lamp-chip--active' : 'lamp-chip'}
                    onClick={() =>
                      updateSelection(detailRecommendation.sku_id, (current) => ({
                        ...current,
                        finish,
                      }))
                    }
                  >
                    {finish}
                  </button>
                ))}
              </div>
            </section>
            <section className="lamp-option-group">
              <h5>数量</h5>
              <div className="lamp-qty-row">
                <button
                  type="button"
                  className="icon-button"
                  onClick={() =>
                    updateSelection(detailRecommendation.sku_id, (current) => ({
                      ...current,
                      qty: clampQty(current.qty - 1),
                    }))
                  }
                >
                  <Minus size={16} />
                </button>
                <strong>{getSelection(detailRecommendation.sku_id).qty}</strong>
                <button
                  type="button"
                  className="icon-button"
                  onClick={() =>
                    updateSelection(detailRecommendation.sku_id, (current) => ({
                      ...current,
                      qty: clampQty(current.qty + 1),
                    }))
                  }
                >
                  <Plus size={16} />
                </button>
              </div>
            </section>
            <button type="button" className="primary-button lamp-sheet__footer-btn" onClick={handleConfirmLampSelection}>
              选好了
            </button>
          </section>
        </div>
      ) : null}

      {storeSheetOpen ? (
        <div className="sheet-backdrop lamp-sheet-backdrop" onClick={() => setStoreSheetOpen(false)}>
          <section className="sheet-panel lamp-sheet lamp-sheet--store" onClick={(event) => event.stopPropagation()}>
            <header className="lamp-store-head">
              <div>
                <strong>精选灯具门店</strong>
                <p>评分 5.0 · 月售 1000+ · 约45分钟送达</p>
              </div>
              <button type="button" className="icon-button" onClick={() => setStoreSheetOpen(false)}>
                <ChevronDown size={18} />
              </button>
            </header>
            <div className="lamp-store-layout">
              <aside className="lamp-store-categories">
                {storeData.categories.map((category) => (
                  <button
                    key={category}
                    type="button"
                    className={category === '猜你喜欢' ? 'lamp-store-category lamp-store-category--active' : 'lamp-store-category'}
                  >
                    {category}
                  </button>
                ))}
              </aside>
              <div className="lamp-store-products">
                {storeData.products.map((product) => (
                  <article key={product.id} className="lamp-store-product">
                    {product.imagePath ? (
                      <img src={buildVisionImageUrl(product.imagePath)} alt={product.name} />
                    ) : (
                      <div className="lamp-store-product__image lamp-store-product__image--empty">暂无图</div>
                    )}
                    <div>
                      <h4>{product.name}</h4>
                      <p>{product.subtitle}</p>
                      <strong>￥{product.price.toFixed(0)}</strong>
                    </div>
                    <button type="button" className="primary-button primary-button--compact" onClick={() => openDetailSheet(product.recommendation.sku_id)}>
                      选规格
                    </button>
                  </article>
                ))}
              </div>
            </div>
            <footer className="lamp-store-footer">
              <div>
                <strong>￥{storeTotal.toFixed(0)}</strong>
                <p>{confirmedItems.length > 0 ? `已选 ${confirmedItems.length} 款灯具` : '请选择灯具规格'}</p>
              </div>
              <button type="button" className="primary-button" onClick={() => setStoreSheetOpen(false)}>
                选好了
              </button>
            </footer>
          </section>
        </div>
      ) : null}
    </article>
  );
}
