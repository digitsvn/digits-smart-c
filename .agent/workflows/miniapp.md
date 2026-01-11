---
description: Hướng dẫn phát triển Zalo MiniApp Shop - Cấu trúc và quy trình làm việc
---

# MiniApp Shop Development Guide

Workflow này hướng dẫn cách xây dựng và phát triển Zalo MiniApp Shop frontend kết nối với BE (DigitsPOS-V6.10).

**📌 Xem thêm:** `/style-miniapp` - Hướng dẫn giao diện và UI/UX

---

## QUY ƯỚC THUẬT NGỮ

| Thuật ngữ | Nghĩa |
|-----------|-------|
| **BE** | Backend - `/wwwroot/DigitsPOS-V6.10` |
| **MiniAppShop** | Frontend - `/wwwroot/MiniAppShop` |
| **Module** | Module ZaloMiniapp trong BE (`Modules/ZaloMiniapp`) |

---

## QUY TẮC API-FIRST VÀ DEMO DATA

> ⚠️ **QUY TẮC QUAN TRỌNG**: Mọi dữ liệu hiển thị trên MiniApp PHẢI lấy từ BE API.
> **Khi làm tính năng mới → Phải tạo Demo Data ở BE để hiển thị.**

### Nguyên tắc chung:

1. **Tất cả hình ảnh phải từ API:**
   - Avatar / Huy hiệu cấp độ thành viên
   - Icon danh mục / Quick Actions
   - Banner / Hình sản phẩm
   - **KHÔNG hardcode URL hình trong frontend**

2. **Tất cả nội dung động phải từ API:**
   - Tên, mô tả các cấp độ thành viên
   - Quyền hạn/Benefits từng cấp độ
   - Phần thưởng, vouchers
   - Màu sắc, icon của từng tier

3. **Khi làm tính năng mới - TỰ TẠO DEMO:**
   ```
   Làm Frontend → Cần dữ liệu → Tạo Demo Data ở BE → Hiển thị trên MiniApp
   ```

### Cấu trúc dữ liệu bắt buộc:

#### Membership Tiers (GET /loyalty/tiers):
```json
{
  "tiers": [
    {
      "id": 1,
      "name": "Thành Viên",
      "icon": "🥉",
      "image": "/images/tiers/member.png",
      "color": "#CD7F32",
      "min_spent": 0,
      "max_spent": 1000000,
      "benefits": ["Tích điểm 1%", "Hỗ trợ qua ZaloOA"]
    }
  ]
}
```

#### User Profile (GET /loyalty/profile):
```json
{
  "user": {
    "name": "Hoài Nguyễn",
    "avatar": "/images/avatars/user.png"
  },
  "points": 142,
  "tier": {
    "id": 1,
    "name": "Thành Viên",
    "icon": "🥉",
    "image": "/images/tiers/member.png"
  },
  "next_tier": {
    "name": "Hạng Bạc",
    "remaining": 858000
  }
}
```

---

## 1. Project Structure

Dựa trên mẫu **ZaUI Fashion** từ Zalo:

```
/wwwroot/MiniAppShop/
├── src/
│   ├── pages/            # App pages (React components)
│   │   ├── home/         # Trang chủ (banners, flash-sale, categories)
│   │   ├── catalog/      # Danh sách sản phẩm
│   │   ├── cart/         # Giỏ hàng
│   │   ├── profile/      # Tài khoản
│   │   └── search/       # Tìm kiếm
│   ├── components/       # Reusable UI components
│   ├── utils/            # Helpers (request.ts, cart.ts, template.ts)
│   ├── state.ts          # Global state (Jotai)
│   ├── hooks.ts          # Custom hooks
│   ├── router.tsx        # Router configuration
│   └── api/              # API services (tích hợp BE)
├── app-config.json       # Zalo app config + API URL
└── package.json
```

---

## 2. Tích hợp API với BE

### 2.1 Cấu hình API URL

**File:** `app-config.json`
```json
{
  "template": {
    "apiUrl": "http://localhost:8001/api/miniapp",  // DEV
    // "apiUrl": "https://your-domain.com/api/miniapp",  // PROD
    "businessId": 1
  }
}
```

### 2.2 Request wrapper

**File:** `src/utils/request.ts`
```typescript
import { getConfig } from "./template";
import { getAccessToken } from "zmp-sdk";

const API_URL = getConfig((config) => config.template.apiUrl);
const BUSINESS_ID = getConfig((config) => config.template.businessId);

export async function apiRequest<T>(
  endpoint: string, 
  options?: RequestInit
): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  
  // Add business_id to query params
  const urlWithParams = new URL(url);
  urlWithParams.searchParams.set('business_id', BUSINESS_ID);
  
  // Get auth token if logged in
  let headers: HeadersInit = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };
  
  try {
    const token = await getAccessToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  } catch {}
  
  const response = await fetch(urlWithParams.toString(), {
    ...options,
    headers: { ...headers, ...options?.headers },
  });
  
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.message || 'API Error');
  }
  
  return data.data as T;
}
```

### 2.3 API Mapping (BE ↔ MiniAppShop)

| BE API Endpoint | MiniAppShop Usage |
|-----------------|-------------------|
| `GET /home` | `state.ts` → bannersState, categoriesState, themeState |
| `GET /products` | `state.ts` → productsState |
| `GET /products/:id` | Product detail page |
| `GET /cart` | `state.ts` → cartState |
| `POST /cart/items` | `hooks.ts` → useAddToCart |
| `POST /orders` | `hooks.ts` → useCheckout |
| `GET /loyalty/profile` | Profile page → loyalty section |

---

## 3. State Management (Jotai)

Cập nhật `src/state.ts` để dùng API từ BE:

```typescript
import { atom } from "jotai";
import { apiRequest } from "@/utils/request";

// Theme từ BE
export const themeState = atom(async () => {
  const home = await apiRequest<HomeData>('/home');
  return home.theme;
});

// Layout order từ BE
export const layoutState = atom(async () => {
  const home = await apiRequest<HomeData>('/home');
  return home.layout;
});

// Banners từ BE  
export const bannersState = atom(async () => {
  const home = await apiRequest<HomeData>('/home');
  return home.banners;
});

// Products từ BE
export const productsState = atom(async () => {
  const { items } = await apiRequest<ProductsResponse>('/products');
  return items;
});

// Cart từ BE (persistent)
export const cartState = atom(async () => {
  try {
    const cart = await apiRequest<CartData>('/cart');
    return cart.items;
  } catch {
    return []; // Not logged in
  }
});
```

---

## 4. Thiếu API? Thêm vào BE Module

Nếu MiniAppShop cần API mà BE chưa có:

### 4.1 Kiểm tra API đã có chưa

```bash
# Xem tất cả routes của Module
cat /wwwroot/DigitsPOS-V6.10/Modules/ZaloMiniapp/Routes/api.php
```

### 4.2 Thêm API mới

Tuân thủ workflow `/module` và `/style-guide`:

```php
// Modules/ZaloMiniapp/Routes/api.php
Route::get('/new-endpoint', [NewController::class, 'method']);

// Modules/ZaloMiniapp/Http/Controllers/Api/NewController.php
public function method(Request $request): JsonResponse
{
    $businessId = $request->input('business_id');
    // ... logic
    return response()->json([
        'success' => true,
        'data' => $result,
    ]);
}
```

---

## 5. Build & Deploy

### ⚠️ QUAN TRỌNG: Phải chạy CẢ BE lẫn MiniAppShop

> **Nếu không chạy BE, MiniAppShop sẽ KHÔNG CÓ DATA!**  
> MiniApp lấy toàn bộ dữ liệu từ API Backend. Nếu BE không chạy → API lỗi → MiniApp hiển thị trống.

### 5.1 Khởi động Development (2 terminal)

**Terminal 1 - Backend (Laravel):**
```bash
cd /Users/nguyenduchoai/wwwroot/DigitsPOS-V6.10
php artisan serve --port=8001
```

**Terminal 2 - MiniApp (React):**
```bash
cd /Users/nguyenduchoai/wwwroot/MiniAppShop/thien-van-yen
npm start               # hoặc: npm run dev / zmp start
```

**Kiểm tra:**
- BE: http://localhost:8001 (Admin Panel)
- MiniApp: http://localhost:3000

### 5.2 Admin Login

| Username | Password | Email |
|----------|----------|-------|
| `admin` | `123456` | admin@digits.vn |
| `hoainguyen` | (đã đổi) | nguyenduchoai@gmail.com |

**Admin Panel URLs:**
- Tổng quan: http://localhost:8001/home
- Zalo MiniApp Settings: http://localhost:8001/zalo-miniapp/settings
- Flash Sales: http://localhost:8001/zalo-miniapp/flash-sales
- Banners: http://localhost:8001/zalo-miniapp/banners
- Theme: http://localhost:8001/zalo-miniapp/settings/theme

### 5.3 Cấu hình API

Edit `app-config.json`:
```json
"template": {
  "apiUrl": "http://localhost:8001/api/miniapp",
  "businessId": 2
}
```

### 5.4 Production Deploy
```bash
zmp login
zmp deploy
```

---

## 6. Checklist Before PR

### Frontend (MiniAppShop):
- [ ] Sử dụng màu từ `themeSettingsState`, KHÔNG hardcode
- [ ] Render sections theo `layout` order từ API
- [ ] Gọi API đúng endpoints
- [ ] Handle loading/error states

### Backend (BE):
- [ ] API trả về đúng format: `{ success: true, data: ... }`
- [ ] Validate business_id
- [ ] Tuân thủ `/module` workflow
- [ ] Tuân thủ `/style-guide` cho admin pages

---

## 7. ⚠️ LƯU Ý QUAN TRỌNG - TRÁNH LỖI CRITICAL

### 7.1 Import/Export Errors (Gây crash toàn bộ app)

> **🚨 SyntaxError này sẽ làm app KHÔNG RENDER được - màn hình trắng/đen!**

```typescript
// ❌ SAI - Export không tồn tại trong state.ts
import { useAuthStore } from '@/state';  // useAuthStore KHÔNG CÓ!

// ✅ ĐÚNG - Sử dụng Jotai atoms thực sự tồn tại
import { useAtomValue } from 'jotai';
import { isRegisteredState, customerState, demoModeState } from '@/state';

// Trong component:
const isLoggedIn = useAtomValue(isRegisteredState);
const customer = useAtomValue(customerState);
```

**Lỗi useNavigate:**
```typescript
// ❌ SAI - Gây lỗi "must be contained with ZMPRouter"
import { useNavigate } from 'zmp-ui';

// ✅ ĐÚNG - React Router DOM (app dùng react-router, KHÔNG dùng ZMPRouter)
import { useNavigate } from 'react-router-dom';
```

### 7.2 Các exports THỰC SỰ có trong state.ts:

| Export | Type | Mô tả |
|--------|------|-------|
| `userState` | atom (async) | Thông tin user từ Zalo SDK |
| `customerState` | atom | Dữ liệu khách hàng đã đăng ký |
| `isRegisteredState` | atom (computed) | Boolean: đã đăng ký chưa |
| `demoModeState` | atom | Boolean: đang ở demo mode |
| `homeDataState` | atom (async) | Dữ liệu trang chủ từ BE |
| `themeState` | atom (async) | Theme settings từ BE |
| `themeSettingsState` | unwrapped atom | Theme sync (dùng trong components) |
| `categoriesState` | atom (async) | Danh mục sản phẩm |
| `productsState` | atom (async) | Danh sách sản phẩm |
| `cartState` | atom | Giỏ hàng local |
| `loyaltyDataState` | atom | Dữ liệu loyalty/điểm thưởng |

### 7.3 Async Atoms và Suspense

> **⚠️ Async atoms CẦN có Suspense boundary!**

Nếu component sử dụng async atom mà không có Suspense wrapper, app sẽ bị treo.

```typescript
// app.ts - Đã có Suspense wrapper ở root
import { createElement, Suspense } from "react";

root.render(
  createElement(
    Suspense,
    { fallback: createElement(LoadingFallback) },
    createElement(RouterProvider, { router })
  )
);
```

### 7.4 Kiểm tra trước khi tạo trang mới

```bash
# Xem tất cả exports trong state.ts
grep "^export " src/state.ts

# Kiểm tra import của một file
head -20 src/pages/your-page/index.tsx
```

---

## 8. Tài liệu tham khảo

- **UI/UX Guide:** Xem `/style-miniapp` workflow
- **BE API Docs:** `BE/Modules/ZaloMiniapp/FRONTEND_API_DOCUMENTATION.md`
- **Template gốc:** `/wwwroot/MiniAppShop/thien-van-yen/`
- **Zalo SDK:** https://miniapp.zaloplatforms.com/documents/api
- **Jotai Docs:** https://jotai.org/docs/basics/primitives
