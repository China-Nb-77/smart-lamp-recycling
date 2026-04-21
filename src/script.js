const STORAGE_KEYS = {
  session: "smart-lamp-assistant:session",
  profile: "smart-lamp-assistant:profile",
  addresses: "smart-lamp-assistant:addresses",
  orders: "smart-lamp-assistant:orders",
};

const PRODUCTS = [
  {
    id: "alu-pendant-s",
    name: "Aluminum Pendant S",
    sku: "SKU-ALU-PENDANT-S",
    size: "Small",
    material: "Aluminum",
    price: 199,
  },
  {
    id: "glass-floor-m",
    name: "Glass Floor M",
    sku: "SKU-GLASS-FLOOR-M",
    size: "Medium",
    material: "Glass",
    price: 329,
  },
];

const DEFAULT_PROFILE = {
  name: "灯光体验官",
  phone: "13800138000",
};

const DEFAULT_ADDRESSES = [
  {
    id: "addr-company",
    label: "公司",
    recipient: "王女士",
    phone: "13800138000",
    detail: "上海市浦东新区世纪大道 100 号 18F",
    isDefault: true,
  },
  {
    id: "addr-home",
    label: "家里",
    recipient: "王女士",
    phone: "13900139000",
    detail: "上海市徐汇区龙腾大道 266 号 1201 室",
    isDefault: false,
  },
];

const state = {
  session: null,
  profile: { ...DEFAULT_PROFILE },
  addresses: [],
  orders: [],
  activeProduct: PRODUCTS[0],
  activeSheet: null,
  editingAddressId: "",
  selectedAddressId: "",
};

const elements = {
  loginScreen: document.getElementById("loginScreen"),
  appScreen: document.getElementById("appScreen"),
  loginForm: document.getElementById("loginForm"),
  nicknameInput: document.getElementById("nicknameInput"),
  phoneInput: document.getElementById("phoneInput"),
  welcomeName: document.getElementById("welcomeName"),
  profileButton: document.getElementById("profileButton"),
  profileButtonAvatar: document.getElementById("profileButtonAvatar"),
  sheetBackdrop: document.getElementById("sheetBackdrop"),
  orderSheet: document.getElementById("orderSheet"),
  profileSheet: document.getElementById("profileSheet"),
  orderForm: document.getElementById("orderForm"),
  orderProductName: document.getElementById("orderProductName"),
  orderProductMeta: document.getElementById("orderProductMeta"),
  orderUnitPrice: document.getElementById("orderUnitPrice"),
  quantityInput: document.getElementById("quantityInput"),
  decreaseQuantity: document.getElementById("decreaseQuantity"),
  increaseQuantity: document.getElementById("increaseQuantity"),
  addressSelect: document.getElementById("addressSelect"),
  manageAddressButton: document.getElementById("manageAddressButton"),
  orderNote: document.getElementById("orderNote"),
  orderTotal: document.getElementById("orderTotal"),
  orderList: document.getElementById("orderList"),
  orderEmptyState: document.getElementById("orderEmptyState"),
  profileAvatar: document.getElementById("profileAvatar"),
  profileNameDisplay: document.getElementById("profileNameDisplay"),
  profilePhoneDisplay: document.getElementById("profilePhoneDisplay"),
  orderCountStat: document.getElementById("orderCountStat"),
  addressCountStat: document.getElementById("addressCountStat"),
  addressList: document.getElementById("addressList"),
  addressForm: document.getElementById("addressForm"),
  addressIdInput: document.getElementById("addressIdInput"),
  addressLabelInput: document.getElementById("addressLabelInput"),
  recipientInput: document.getElementById("recipientInput"),
  addressPhoneInput: document.getElementById("addressPhoneInput"),
  addressDetailInput: document.getElementById("addressDetailInput"),
  addressDefaultInput: document.getElementById("addressDefaultInput"),
  resetAddressButton: document.getElementById("resetAddressButton"),
  logoutButton: document.getElementById("logoutButton"),
  toast: document.getElementById("toast"),
};

let toastTimer = null;

function readJson(key, fallbackValue) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallbackValue;
  } catch (error) {
    return fallbackValue;
  }
}

function writeJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function uid(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatCurrency(value) {
  return `¥${Number(value).toFixed(0)}`;
}

function formatDate(value) {
  const date = new Date(value);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");
  return `${month}/${day} ${hour}:${minute}`;
}

function initials(name) {
  const text = String(name || "灯").trim();
  return text ? text.slice(0, 1).toUpperCase() : "灯";
}

function normalizeAddresses(addresses) {
  const normalized = Array.isArray(addresses)
    ? addresses.map((address, index) => ({
        id: address.id || uid("addr"),
        label: address.label || `地址${index + 1}`,
        recipient: address.recipient || state.profile.name,
        phone: address.phone || state.profile.phone,
        detail: address.detail || "",
        isDefault: Boolean(address.isDefault),
      }))
    : [];

  if (!normalized.length) {
    return DEFAULT_ADDRESSES.map((address) => ({ ...address }));
  }

  if (!normalized.some((address) => address.isDefault)) {
    normalized[0].isDefault = true;
  }

  return normalized;
}

function defaultAddress() {
  return state.addresses.find((address) => address.isDefault) || state.addresses[0] || null;
}

function getProduct(productId) {
  return PRODUCTS.find((product) => product.id === productId) || PRODUCTS[0];
}

function getQuantity() {
  const parsed = Number.parseInt(elements.quantityInput.value, 10);
  if (!Number.isFinite(parsed)) {
    return 1;
  }
  return Math.min(9, Math.max(1, parsed));
}

function syncQuantity(nextQuantity) {
  const quantity = Math.min(9, Math.max(1, Number(nextQuantity) || 1));
  elements.quantityInput.value = String(quantity);
  updateOrderTotal();
}

function loadState() {
  state.profile = {
    ...DEFAULT_PROFILE,
    ...readJson(STORAGE_KEYS.profile, DEFAULT_PROFILE),
  };
  state.session = readJson(STORAGE_KEYS.session, null);
  state.addresses = normalizeAddresses(readJson(STORAGE_KEYS.addresses, DEFAULT_ADDRESSES));
  state.orders = Array.isArray(readJson(STORAGE_KEYS.orders, []))
    ? readJson(STORAGE_KEYS.orders, [])
    : [];
  state.selectedAddressId = defaultAddress()?.id || "";
}

function saveProfile() {
  writeJson(STORAGE_KEYS.profile, state.profile);
}

function saveSession() {
  if (state.session) {
    writeJson(STORAGE_KEYS.session, state.session);
  } else {
    localStorage.removeItem(STORAGE_KEYS.session);
  }
}

function saveAddresses() {
  writeJson(STORAGE_KEYS.addresses, state.addresses);
}

function saveOrders() {
  writeJson(STORAGE_KEYS.orders, state.orders);
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    elements.toast.classList.remove("is-visible");
  }, 2200);
}

function renderScreen() {
  const isLoggedIn = Boolean(state.session?.loggedIn);
  elements.loginScreen.classList.toggle("hidden", isLoggedIn);
  elements.appScreen.classList.toggle("hidden", !isLoggedIn);

  if (!isLoggedIn) {
    elements.nicknameInput.value = state.profile.name || "";
    elements.phoneInput.value = state.profile.phone || "";
    closeSheets();
    return;
  }

  renderApp();
}

function renderOrders() {
  if (!state.orders.length) {
    elements.orderEmptyState.classList.remove("hidden");
    elements.orderList.innerHTML = "";
    return;
  }

  elements.orderEmptyState.classList.add("hidden");
  elements.orderList.innerHTML = state.orders
    .map(
      (order) => `
        <article class="order-card">
          <strong>${escapeHtml(order.productName)} × ${order.quantity}</strong>
          <div class="order-meta">
            <span>${formatCurrency(order.total)}</span>
            <span>${escapeHtml(order.addressLabel)}</span>
            <span>${escapeHtml(formatDate(order.createdAt))}</span>
          </div>
          <div class="order-meta">
            <span>${escapeHtml(order.note || "无备注")}</span>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderAddressSelect() {
  if (!state.addresses.length) {
    elements.addressSelect.innerHTML = '<option value="">请先在个人中心新增地址</option>';
    return;
  }

  if (!state.addresses.some((address) => address.id === state.selectedAddressId)) {
    state.selectedAddressId = defaultAddress()?.id || state.addresses[0].id;
  }

  elements.addressSelect.innerHTML = state.addresses
    .map(
      (address) => `
        <option value="${escapeHtml(address.id)}" ${
          address.id === state.selectedAddressId ? "selected" : ""
        }>
          ${escapeHtml(`${address.label} · ${address.recipient} · ${address.detail}`)}
        </option>
      `,
    )
    .join("");
}

function renderOrderTotal() {
  const total = state.activeProduct.price * getQuantity();
  elements.orderTotal.textContent = formatCurrency(total);
}

function renderOrderSheet() {
  const product = state.activeProduct;
  elements.orderProductName.textContent = product.name;
  elements.orderProductMeta.textContent = `${product.sku} · ${product.size} · ${product.material}`;
  elements.orderUnitPrice.textContent = formatCurrency(product.price);
  renderAddressSelect();
  renderOrderTotal();
}

function renderProfile() {
  const name = state.session?.name || state.profile.name;
  const phone = state.session?.phone || state.profile.phone;

  elements.welcomeName.textContent = name;
  elements.profileNameDisplay.textContent = name;
  elements.profilePhoneDisplay.textContent = phone;
  elements.profileAvatar.textContent = initials(name);
  elements.profileButtonAvatar.textContent = initials(name);
  elements.orderCountStat.textContent = String(state.orders.length);
  elements.addressCountStat.textContent = String(state.addresses.length);

  elements.addressList.innerHTML = state.addresses
    .map(
      (address) => `
        <article class="address-card ${address.isDefault ? "is-default" : ""}">
          <div class="address-topline">
            <strong>${escapeHtml(address.label)}</strong>
            ${
              address.isDefault
                ? '<span class="default-tag">默认地址</span>'
                : ""
            }
          </div>
          <div class="address-copy">
            ${escapeHtml(address.recipient)} · ${escapeHtml(address.phone)}
          </div>
          <div class="address-copy">${escapeHtml(address.detail)}</div>
          <div class="address-actions">
            <button
              class="mini-button secondary"
              type="button"
              data-address-action="select"
              data-address-id="${escapeHtml(address.id)}"
            >
              ${address.isDefault ? "当前默认" : "设为默认"}
            </button>
            <button
              class="mini-button"
              type="button"
              data-address-action="edit"
              data-address-id="${escapeHtml(address.id)}"
            >
              编辑
            </button>
            <button
              class="mini-button danger"
              type="button"
              data-address-action="delete"
              data-address-id="${escapeHtml(address.id)}"
            >
              删除
            </button>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderApp() {
  renderOrders();
  renderOrderSheet();
  renderProfile();
}

function openSheet(name) {
  state.activeSheet = name;
  elements.sheetBackdrop.classList.add("is-visible");
  elements.orderSheet.classList.toggle("is-open", name === "order");
  elements.profileSheet.classList.toggle("is-open", name === "profile");
  elements.orderSheet.setAttribute("aria-hidden", String(name !== "order"));
  elements.profileSheet.setAttribute("aria-hidden", String(name !== "profile"));
  document.body.classList.add("sheet-open");
}

function closeSheets() {
  state.activeSheet = null;
  elements.sheetBackdrop.classList.remove("is-visible");
  elements.orderSheet.classList.remove("is-open");
  elements.profileSheet.classList.remove("is-open");
  elements.orderSheet.setAttribute("aria-hidden", "true");
  elements.profileSheet.setAttribute("aria-hidden", "true");
  document.body.classList.remove("sheet-open");
}

function resetAddressForm() {
  state.editingAddressId = "";
  elements.addressIdInput.value = "";
  elements.addressLabelInput.value = "";
  elements.recipientInput.value = state.session?.name || state.profile.name;
  elements.addressPhoneInput.value = state.session?.phone || state.profile.phone;
  elements.addressDetailInput.value = "";
  elements.addressDefaultInput.checked = state.addresses.length === 0;
}

function fillAddressForm(addressId) {
  const address = state.addresses.find((item) => item.id === addressId);
  if (!address) {
    return;
  }

  state.editingAddressId = address.id;
  elements.addressIdInput.value = address.id;
  elements.addressLabelInput.value = address.label;
  elements.recipientInput.value = address.recipient;
  elements.addressPhoneInput.value = address.phone;
  elements.addressDetailInput.value = address.detail;
  elements.addressDefaultInput.checked = address.isDefault;
}

function selectDefaultAddress(addressId) {
  state.addresses = state.addresses.map((address) => ({
    ...address,
    isDefault: address.id === addressId,
  }));
  state.selectedAddressId = addressId;
  saveAddresses();
  renderApp();
}

function deleteAddress(addressId) {
  if (state.addresses.length === 1) {
    showToast("请至少保留一个地址用于下单");
    return;
  }

  state.addresses = state.addresses.filter((address) => address.id !== addressId);
  state.addresses = normalizeAddresses(state.addresses);
  state.selectedAddressId = defaultAddress()?.id || "";
  saveAddresses();
  renderApp();
  resetAddressForm();
  showToast("地址已删除");
}

function handleAddressAction(event) {
  const trigger = event.target.closest("[data-address-action]");
  if (!trigger) {
    return;
  }

  const action = trigger.getAttribute("data-address-action");
  const addressId = trigger.getAttribute("data-address-id");

  if (!addressId) {
    return;
  }

  if (action === "select") {
    selectDefaultAddress(addressId);
    showToast("默认地址已更新");
    return;
  }

  if (action === "edit") {
    fillAddressForm(addressId);
    showToast("已载入地址信息");
    return;
  }

  if (action === "delete") {
    deleteAddress(addressId);
  }
}

function handleLoginSubmit(event) {
  event.preventDefault();

  const name = elements.nicknameInput.value.trim();
  const phone = elements.phoneInput.value.trim();

  state.profile = {
    name: name || DEFAULT_PROFILE.name,
    phone: phone || DEFAULT_PROFILE.phone,
  };
  state.session = {
    id: uid("session"),
    name: state.profile.name,
    phone: state.profile.phone,
    loggedIn: true,
    loggedInAt: new Date().toISOString(),
  };

  saveProfile();
  saveSession();
  state.addresses = normalizeAddresses(state.addresses);
  saveAddresses();
  renderScreen();
  showToast(`欢迎回来，${state.profile.name}`);
}

function handleChooseProduct(event) {
  const button = event.target.closest(".choose-button");
  if (!button) {
    return;
  }

  state.activeProduct = getProduct(button.getAttribute("data-product-id"));
  state.selectedAddressId = defaultAddress()?.id || "";
  syncQuantity(1);
  elements.orderNote.value = "";
  renderOrderSheet();
  openSheet("order");
}

function handleOrderSubmit(event) {
  event.preventDefault();

  if (!state.addresses.length) {
    openSheet("profile");
    showToast("请先在个人中心新增地址");
    return;
  }

  const address =
    state.addresses.find((item) => item.id === elements.addressSelect.value) ||
    defaultAddress();
  const quantity = getQuantity();
  const total = state.activeProduct.price * quantity;

  const order = {
    id: uid("order"),
    productId: state.activeProduct.id,
    productName: state.activeProduct.name,
    quantity,
    total,
    addressId: address.id,
    addressLabel: address.label,
    note: elements.orderNote.value.trim(),
    createdAt: new Date().toISOString(),
  };

  state.orders.unshift(order);
  saveOrders();
  renderOrders();
  renderProfile();
  closeSheets();
  showToast(`订单已提交：${order.productName} × ${order.quantity}`);
}

function handleAddressFormSubmit(event) {
  event.preventDefault();

  const payload = {
    id: state.editingAddressId || uid("addr"),
    label: elements.addressLabelInput.value.trim(),
    recipient: elements.recipientInput.value.trim(),
    phone: elements.addressPhoneInput.value.trim(),
    detail: elements.addressDetailInput.value.trim(),
    isDefault: elements.addressDefaultInput.checked,
  };

  if (!payload.label || !payload.recipient || !payload.phone || !payload.detail) {
    showToast("请完整填写地址信息");
    return;
  }

  if (state.editingAddressId) {
    state.addresses = state.addresses.map((address) =>
      address.id === state.editingAddressId ? payload : address,
    );
  } else {
    state.addresses.push(payload);
  }

  if (payload.isDefault || state.addresses.length === 1) {
    state.addresses = state.addresses.map((address) => ({
      ...address,
      isDefault: address.id === payload.id,
    }));
    state.selectedAddressId = payload.id;
  }

  state.addresses = normalizeAddresses(state.addresses);
  saveAddresses();
  renderApp();
  resetAddressForm();
  showToast(state.editingAddressId ? "地址已更新" : "地址已新增");
}

function handleLogout() {
  state.session = null;
  saveSession();
  closeSheets();
  renderScreen();
  showToast("已退出登录");
}

function bindEvents() {
  elements.loginForm.addEventListener("submit", handleLoginSubmit);
  document.addEventListener("click", handleChooseProduct);
  elements.profileButton.addEventListener("click", () => {
    renderProfile();
    openSheet("profile");
  });
  elements.sheetBackdrop.addEventListener("click", closeSheets);

  document.querySelectorAll("[data-close-sheet]").forEach((button) => {
    button.addEventListener("click", closeSheets);
  });

  elements.decreaseQuantity.addEventListener("click", () => {
    syncQuantity(getQuantity() - 1);
  });
  elements.increaseQuantity.addEventListener("click", () => {
    syncQuantity(getQuantity() + 1);
  });
  elements.quantityInput.addEventListener("input", () => {
    syncQuantity(getQuantity());
  });
  elements.addressSelect.addEventListener("change", (event) => {
    state.selectedAddressId = event.target.value;
  });
  elements.manageAddressButton.addEventListener("click", () => {
    renderProfile();
    openSheet("profile");
  });
  elements.orderForm.addEventListener("submit", handleOrderSubmit);
  elements.addressForm.addEventListener("submit", handleAddressFormSubmit);
  elements.addressList.addEventListener("click", handleAddressAction);
  elements.resetAddressButton.addEventListener("click", resetAddressForm);
  elements.logoutButton.addEventListener("click", handleLogout);
}

function init() {
  loadState();
  bindEvents();
  resetAddressForm();
  renderScreen();
}

init();
