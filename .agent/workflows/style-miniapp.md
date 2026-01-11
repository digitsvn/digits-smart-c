---
description: Hướng dẫn Style và Giao diện cho Zalo MiniApp Shop
---

# MiniApp Style Guide

Tài liệu này hướng dẫn chuẩn UI/UX và giao diện cho Zalo MiniApp Shop.

**📌 Xem thêm:** `/miniapp` - Hướng dẫn cấu trúc và quy trình phát triển

---

## ⚠️ NGUYÊN TẮC QUAN TRỌNG NHẤT

### 🎨 MÀU SẮC PHẢI LẤY TỪ SETTINGS

> **QUY TẮC VÀNG**: Tất cả màu sắc PHẢI lấy từ `themeSettingsState` (API Settings).
> **TUYỆT ĐỐI KHÔNG ĐƯỢC hardcode màu vào code MiniApp!**

```typescript
// ✅ ĐÚNG - Lấy màu từ Settings
import { useAtomValue } from "jotai";
import { themeSettingsState } from "@/state";

const themeSettings = useAtomValue(themeSettingsState);
const primaryColor = themeSettings.primary_color || '#4CAF50';
const headerBgFrom = themeSettings.header_bg_from || primaryColor;
const headerBgTo = themeSettings.header_bg_to || primaryColor;

<div style={{ backgroundColor: primaryColor }}>...</div>
<div style={{ background: `linear-gradient(135deg, ${headerBgFrom}, ${headerBgTo})` }}>...</div>

// ❌ SAI - Hardcode màu
<div className="bg-green-500">...</div>
<div style={{ background: 'linear-gradient(135deg, #4CAF50, #8BC34A)' }}>...</div>
```

### Theme Settings State

```typescript
// src/state.ts
export const themeSettingsState = atom<ThemeSettings>({
  primary_color: '#4CAF50',
  secondary_color: '#8BC34A',
  header_bg_from: '#4CAF50',
  header_bg_to: '#8BC34A',
  // ... lấy từ API /home → settings
});
```

### Áp dụng cho TẤT CẢ các trang:

| Trang | Elements cần dùng màu từ Settings |
|-------|-----------------------------------|
| **Home** | Header gradient, Quick actions, Section titles |
| **Profile** | Header, Avatar border, Buttons, Stats |
| **Promotions** | Header gradient, Voucher cards, Buttons |
| **Loyalty** | Header, Tier badges, Progress bars, Buttons |
| **Cart** | Buttons, Price highlights |
| **Product** | Add to cart button, Price, Sale badge |

### ⚠️ QUY TẮC HEADER TRANG CON

> **BẮT BUỘC**: Tất cả header của trang con (Promotions, Profile, Loyalty, Cart...) phải dùng:
> - **Màu nền**: `primary_color` với **opacity 70%** (`${primaryColor}B3`)
> - **Chữ**: Màu trắng (`#FFFFFF`)

```tsx
// ✅ CHUẨN - Header trang con với opacity 70%
const themeSettings = useAtomValue(themeSettingsState);
const primaryColor = themeSettings.primary_color || '#4CAF50';
const headerBg = `${primaryColor}B3`; // B3 = 70% opacity

<div 
  className="px-4 py-4"
  style={{ backgroundColor: headerBg }}
>
  <p className="text-white font-bold text-lg">Tiêu đề trang</p>
  <p className="text-white/80 text-sm">Mô tả</p>
</div>

// ❌ SAI - Dùng gradient hoặc 100% opacity
style={{ background: `linear-gradient(135deg, ${from}, ${to})` }}
style={{ backgroundColor: primaryColor }} // 100% opacity
```

---

## 1. QUY TẮC UI BẮT BUỘC

### 1.1 Links & Navigation

**Mọi element có thể click PHẢI có link đến trang tương ứng:**

| Element | Navigate to |
|---------|-------------|
| User Info Section | `/profile` |
| Điểm thưởng / Thành viên | `/loyalty` |
| Quick Actions | URL từ BE Settings |
| Categories | `/category/:id` |
| Products | `/product/:id` |
| Vouchers | `/promotions` hoặc `/loyalty` |

### 1.2 Quick Actions (4 nút chức năng)

- **BẮT BUỘC lấy từ BE** - `GET /home` → `quick_actions`
- **Mỗi action có:** `id`, `name`, `icon`, `url`, `color`, `bgColor`, `image`
- **Cấu hình trong:** BE → Module ZaloMiniapp → Settings → Quick Actions
- **KHÔNG được hardcode** default actions trong code

### 1.3 Danh mục (Categories)

- **Layout:** 2 hàng x 4 cột (tối đa 8 items)
- **Thứ tự:** Lấy từ BE Settings (`category_order`)
- **Mỗi category có:** `id`, `name`, `icon`, `image`, `color`

---

## 2. Bo tròn góc (Rounded Corners) - BẮT BUỘC

> ⚠️ **Tất cả UI elements phải bo tròn góc để đồng bộ và đẹp**

| Element | Border Radius |
|---------|---------------|
| **Hình ảnh (images)** | `rounded-lg` (8px) hoặc `rounded-xl` (12px) |
| **Banners** | `rounded-xl` (12px) |
| **Cards/Grid items** | `rounded-xl` (12px) |
| **Buttons** | `rounded-lg` (8px) hoặc `rounded-full` |
| **Input fields** | `rounded-lg` (8px) |
| **Avatars** | `rounded-full` |
| **Badges/Tags** | `rounded-full` hoặc `rounded-lg` |
| **Sections/Containers** | `rounded-xl` (12px) |

```tsx
// ✅ ĐÚNG
<img className="rounded-xl" src={banner} />
<div className="bg-white rounded-xl p-4">...</div>
<button className="rounded-lg px-4 py-2" style={{ backgroundColor: primaryColor }}>...</button>

// ❌ SAI - Không bo góc
<img src={banner} />
<div className="bg-white p-4">...</div>
```

---

## 3. Cấu hình Màu sắc & Nền từ BE Settings

### 3.1 Theme Response từ API

```typescript
// API /home response
{
  "theme": {
    "colors": { 
      "primary": "#9E1E22", 
      "secondary": "#D4AF37",
      "accent": "#D4AF37",
      "background": "#FFFBF5",
      "text": "#333333"
    },
    "buttons": { 
      "border_radius": 8, 
      "primary_bg": "#9E1E22",
      "primary_text": "#FFFFFF"
    },
    "sections": {
      "banners": { "bg_type": "image", "bg": "url_to_image" },
      "quick_actions": { "bg_type": "gradient", "bg": "linear-gradient(135deg, #FFF, #F5F5F5)" },
      "categories": { "bg_type": "color", "bg": "#FFFFFF" },
      "flash_sale": { "bg_type": "gradient", "bg": "linear-gradient(135deg, #4CAF50, #8BC34A)" },
      "products": { 
        "bg_type": "color", 
        "bg": "#F5F5F5",
        "text_color": "#333333"
      }
    },
    "typography": {
      "heading_size": 16,
      "body_size": 14,
      "caption_size": 12,
      "heading_color": "#333333",
      "body_color": "#666666"
    }
  }
}
```

### 3.2 Các loại nền hỗ trợ

| bg_type | Ví dụ |
|---------|-------|
| `color` | `"#FFFFFF"` |
| `gradient` | `"linear-gradient(135deg, #4CAF50, #8BC34A)"` |
| `image` | `"https://example.com/bg.jpg"` |

### 3.3 Áp dụng nền trong React

```tsx
function Section({ sectionId, children }) {
  const themeSettings = useAtomValue(themeSettingsState);
  const sectionStyle = themeSettings.sections?.[sectionId];
  
  const bgStyle = sectionStyle?.bg_type === 'image' 
    ? { backgroundImage: `url(${sectionStyle.bg})`, backgroundSize: 'cover' }
    : sectionStyle?.bg_type === 'gradient'
      ? { background: sectionStyle.bg }
      : { backgroundColor: sectionStyle?.bg || '#FFFFFF' };
  
  return <div style={bgStyle}>{children}</div>;
}
```

### 3.4 Helper: getSectionStyle (BẮT BUỘC dùng cho Loyalty, Promotions)

```tsx
// Helper để tạo style từ section config
const getSectionStyle = (section: any): React.CSSProperties => {
  if (!section) return {};
  
  const { bg, bg_type, padding, text_color, title_color, border_radius } = section;
  
  let style: React.CSSProperties = {
    padding: padding ? `${padding}px` : undefined,
    borderRadius: border_radius ? `${border_radius}px` : undefined,
  };
  
  if (bg_type === 'image' && bg) {
    style.backgroundImage = bg.startsWith('url(') ? bg : `url(${bg})`;
    style.backgroundSize = 'cover';
    style.backgroundPosition = 'center';
  } else if (bg_type === 'gradient' && bg) {
    style.background = bg;
  } else if (bg_type === 'color' && bg) {
    style.backgroundColor = bg;
  }
  
  return style;
};

// Sử dụng
const theme = useAtomValue(themeState);
const sections = (theme as any)?.sections || {};
const userInfoSection = sections.user_info || {};
const couponSection = sections.coupon || {};

<div style={getSectionStyle(userInfoSection)}>
  Header content...
</div>
```

### 3.5 Sections có sẵn từ BE

| Section ID | Sử dụng cho |
|------------|-------------|
| `user_info` | Header trang Profile, Loyalty |
| `coupon` | Block quà tặng, vouchers |
| `banner` | Banners section |
| `categories` | Danh mục |
| `flash_sale` | Flash sale section |
| `quick_actions` | 4 nút chức năng |
| `featured` | Sản phẩm nổi bật |
| `new_products` | Sản phẩm mới |
| `notification` | Thông báo |
| `recent_posts` | Bài viết gần đây |
| `oa_follow` | Follow OA section |

---

## 4. Helper Functions cho Màu sắc

### 4.1 Tạo màu nhạt hơn (transparency)

```typescript
// Thêm transparency vào màu hex
const lightenColor = (color: string, percent: number = 15) => {
  return `${color}${Math.round(255 * percent / 100).toString(16).padStart(2, '0')}`;
};

// Sử dụng
const bgLight = lightenColor(primaryColor, 10); // "#4CAF501A" (10% opacity)
const bgMedium = lightenColor(primaryColor, 20); // "#4CAF5033" (20% opacity)
```

### 4.2 Gradient từ màu chính

```typescript
const getHeaderGradient = (themeSettings) => {
  const from = themeSettings.header_bg_from || themeSettings.primary_color;
  const to = themeSettings.header_bg_to || themeSettings.primary_color;
  return `linear-gradient(135deg, ${from}, ${to})`;
};
```

---

## 5. Ví dụ: Shop Yến Sào Cao Cấp

```json
{
  "theme_colors": {
    "primary": "#9E1E22",      // Đỏ đô - Sang trọng
    "secondary": "#D4AF37",    // Vàng Gold - Cao cấp
    "accent": "#D4AF37",
    "background": "#FFFBF5",   // Kem nhạt - Ấm cúng
    "card": "#FFFFFF",
    "text": "#333333",
    "text_secondary": "#666666"
  },
  "button_styles": {
    "border_radius": 6,
    "primary_bg": "#9E1E22",
    "primary_text": "#FFFFFF"
  }
}
```

---

## 6. Áp dụng Theme vào CSS Variables

```typescript
// Khi load app, set CSS variables từ API
const applyTheme = (theme) => {
  document.documentElement.style.setProperty('--primary', theme.colors.primary);
  document.documentElement.style.setProperty('--color-primary', theme.colors.primary);
  document.documentElement.style.setProperty('--secondary', theme.colors.secondary);
  document.documentElement.style.setProperty('--background', theme.colors.background);
};
```

```css
/* Sử dụng trong CSS/Tailwind */
.btn-primary {
  background-color: var(--primary);
}
```

---

## 7. Cấu hình Theme từ BE Admin Panel

Truy cập: **BE → Zalo MiniApp → Giao diện** để cấu hình:

- **Bảng màu**: Primary, Secondary, Accent, Background, Text...
- **Button Styles**: Bo góc, màu nền, màu chữ
- **Section Backgrounds**: Màu đơn / Gradient / Ảnh nền
- **Typography**: Kích thước chữ, màu chữ
- **Layout Order**: Kéo thả sắp xếp thứ tự sections
- **Quick Actions**: 4 nút với icon, tên, URL, màu sắc

---

## 8. Checklist UI/UX

### Màu sắc:
- [ ] Tất cả màu lấy từ `themeSettingsState`
- [ ] Header gradient dùng `header_bg_from` + `header_bg_to`
- [ ] Buttons dùng `primary_color`
- [ ] Accent colors dùng `secondary_color`
- [ ] KHÔNG có hardcode màu (#xxx) trong code

### Layout:
- [ ] Tất cả cards/images có bo góc (`rounded-xl` hoặc `rounded-lg`)
- [ ] Avatars có `rounded-full`
- [ ] Buttons có `rounded-lg` hoặc `rounded-full`
- [ ] Sections có padding đều (`p-4` hoặc `px-4 py-4`)

### Navigation:
- [ ] Mọi element click được đều có link
- [ ] Quick Actions lấy URL từ BE
- [ ] User Section click → Profile
- [ ] Points/Tier click → Loyalty

### Responsive:
- [ ] Test trên màn hình nhỏ (iPhone SE)
- [ ] Test trên màn hình lớn (iPhone 14 Pro Max)
- [ ] Không có scroll ngang

---

## 9. Ví dụ Component chuẩn

### Header với Gradient từ Settings

```tsx
import { useAtomValue } from "jotai";
import { themeSettingsState } from "@/state";

function PageHeader({ title, subtitle }) {
  const themeSettings = useAtomValue(themeSettingsState);
  
  const headerBg = `linear-gradient(135deg, ${
    themeSettings.header_bg_from || themeSettings.primary_color
  }, ${
    themeSettings.header_bg_to || themeSettings.primary_color
  })`;
  
  return (
    <div className="px-4 py-4" style={{ background: headerBg }}>
      <p className="text-white font-bold text-lg">{title}</p>
      {subtitle && <p className="text-white/80 text-sm">{subtitle}</p>}
    </div>
  );
}
```

### Button với màu từ Settings

```tsx
function PrimaryButton({ children, onClick, disabled }) {
  const themeSettings = useAtomValue(themeSettingsState);
  const primaryColor = themeSettings.primary_color || '#4CAF50';
  
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-4 py-2 text-white font-medium rounded-lg disabled:opacity-50"
      style={{ backgroundColor: primaryColor }}
    >
      {children}
    </button>
  );
}
```

### Card với màu nhạt từ Settings

```tsx
function HighlightCard({ title, content }) {
  const themeSettings = useAtomValue(themeSettingsState);
  const primaryColor = themeSettings.primary_color || '#4CAF50';
  const bgColor = `${primaryColor}15`; // 15% opacity
  
  return (
    <div 
      className="rounded-xl p-4"
      style={{ 
        backgroundColor: bgColor,
        borderLeft: `4px solid ${primaryColor}`
      }}
    >
      <h3 className="font-bold" style={{ color: primaryColor }}>{title}</h3>
      <p className="text-gray-600 text-sm">{content}</p>
    </div>
  );
}
```
