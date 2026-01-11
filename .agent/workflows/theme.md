# Hướng dẫn tạo Theme WebShop

## Tổng quan

WebShop sử dụng kiến trúc **Theme-based** với tất cả dữ liệu hiển thị được lấy từ **Admin Settings** (Module WebshopSettings). Không được phép hardcode bất kỳ thông tin business nào.

---

## 1. Nguyên tắc quan trọng

### ⛔ NGHIÊM CẤM
- Hardcode business name, logo, hotline, email
- Hardcode màu sắc cố định trong components
- Hardcode social links, địa chỉ
- Hardcode giá, tên sản phẩm, nội dung

### ✅ BẮT BUỘC
- Tất cả dữ liệu lấy từ `useSiteConfig()` hook
- Màu sắc qua CSS variables `var(--color-*)`
- Text qua i18n translation `t('key')`
- Content từ API endpoints

---

## 2. Cấu trúc Theme

```
webshop/src/themes/{theme-name}/
├── components/           # UI Components
│   ├── Header/
│   │   ├── Header.tsx
│   │   ├── Topbar.tsx
│   │   ├── MainNav.tsx
│   │   └── index.ts
│   ├── Footer/
│   │   ├── Footer.tsx
│   │   └── index.ts
│   ├── Home/
│   │   ├── HeroBanner.tsx
│   │   ├── FeaturedProducts.tsx
│   │   ├── CategorySection.tsx
│   │   └── NewsSection.tsx
│   └── Common/
│       ├── ProductCard.tsx
│       ├── Button.tsx
│       └── Loading.tsx
├── layouts/              # Page layouts
│   ├── RootLayout.tsx
│   └── index.ts
├── providers/            # Context providers
│   ├── ThemeProvider.tsx
│   └── index.ts
├── styles/               # CSS & theme config
│   ├── theme.config.ts   # Color palette, fonts, spacing
│   ├── global.css        # CSS variables
│   └── index.css
├── i18n/                 # Translations
│   ├── vi.ts
│   ├── en.ts
│   └── index.ts
└── index.ts              # Theme exports
```

---

## 3. Data Sources (Nguồn dữ liệu)

### 3.1. Admin Settings (`useSiteConfig()`)

```typescript
const siteConfig = useSiteConfig();

// Business info
siteConfig.business.name      // Tên shop
siteConfig.business.logo      // Logo URL
siteConfig.business.hotline   // Hotline

// Contact (từ Admin Settings)
siteConfig.contact.business_name
siteConfig.contact.email
siteConfig.contact.hotline
siteConfig.contact.address
siteConfig.contact.working_hours

// Social links (từ Admin Settings)
siteConfig.social.facebook
siteConfig.social.instagram
siteConfig.social.youtube
siteConfig.social.tiktok
siteConfig.social.zalo

// Flash sale
siteConfig.flash_sale.enabled
siteConfig.flash_sale.title
siteConfig.flash_sale.end_time
siteConfig.flash_sale.product_ids

// Theme colors (override từ Admin)
siteConfig.theme_colors.primary
siteConfig.theme_colors.secondary

// Banners
siteConfig.banners[]

// Menu
siteConfig.menu[]

// Promo bar
siteConfig.promo.text
siteConfig.promo.link
```

### 3.2. API Endpoints

| Endpoint | Dữ liệu |
|----------|---------|
| `GET /config` | Site config, theme, contact, social |
| `GET /products` | Sản phẩm |
| `GET /categories` | Danh mục |
| `GET /banners` | Banner |
| `GET /pages/{slug}` | Static pages (policy, about) |

---

## 4. CSS Variables

Theme sử dụng CSS variables được apply từ Admin Settings:

```css
:root {
    /* Colors - sẽ được override bởi Admin Settings */
    --color-primary: #004D43;
    --color-primary-dark: #003830;
    --color-primary-light: #006656;
    --color-secondary: #D4AF37;
    --color-accent: #8B4513;
    
    /* Text */
    --color-text: #333333;
    --color-text-light: #666666;
    --color-text-muted: #999999;
    --color-text-inverse: #FFFFFF;
    
    /* Background */
    --color-background: #FFFFFF;
    --color-background-alt: #F8F6F0;
    
    /* Spacing */
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
    --spacing-xl: 32px;
    
    /* Border radius */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-full: 9999px;
    
    /* Shadows */
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
    
    /* Transitions */
    --transition-fast: 150ms ease;
    --transition-normal: 300ms ease;
}
```

---

## 5. Tạo Theme mới

### Step 1: Copy theme template

```bash
cp -r webshop/src/themes/thienvanyen webshop/src/themes/{new-theme}
```

### Step 2: Update theme.config.ts

```typescript
// themes/{new-theme}/styles/theme.config.ts
export const themeConfig: ThemeConfig = {
    name: 'new-theme',
    displayName: 'New Theme',
    
    colors: {
        primary: '#1a1a2e',       // Màu chủ đạo
        primaryDark: '#0f0f1a',
        primaryLight: '#2d2d4a',
        secondary: '#eab308',     // Màu phụ
        accent: '#10b981',        // Accent color
        
        // ... các màu khác
    },
    
    fonts: {
        primary: '"Inter", sans-serif',
        secondary: '"Playfair Display", serif',
    },
    
    breakpoints: {
        sm: 480,
        md: 768,
        lg: 1024,
        xl: 1280,
    },
};
```

### Step 3: Update global.css

```css
/* themes/{new-theme}/styles/global.css */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --color-primary: #1a1a2e;
    --color-secondary: #eab308;
    /* ... */
}
```

### Step 4: Customize components (nếu cần)

Components có thể được customize nhưng **PHẢI** tuân theo:
- Dùng `useSiteConfig()` cho data
- Dùng `var(--color-*)` cho màu sắc
- Dùng `t('key')` cho text

```tsx
// Ví dụ Footer component
export function Footer() {
    const siteConfig = useSiteConfig();
    const { t } = useTranslation();
    
    // ✅ ĐÚNG: Lấy từ Admin Settings
    const contact = siteConfig?.contact;
    const social = siteConfig?.social;
    
    return (
        <footer style={{ background: 'var(--color-primary)' }}>
            <h4>{contact?.business_name}</h4>
            <p>{contact?.hotline}</p>
            {social?.facebook && (
                <a href={social.facebook}>Facebook</a>
            )}
        </footer>
    );
}
```

### Step 5: Register theme

```typescript
// webshop/src/themes/index.ts
export { ThemeProvider as NewThemeProvider } from './new-theme';
```

---

## 6. Checklist khi tạo Theme

### Data Sources
- [ ] Không hardcode business name
- [ ] Không hardcode contact info
- [ ] Không hardcode social links
- [ ] Không hardcode giá, sản phẩm
- [ ] Sử dụng `useSiteConfig()` cho tất cả config

### Styling
- [ ] Sử dụng CSS variables cho màu sắc
- [ ] Support dark mode (nếu có)
- [ ] Responsive design (Desktop, Mobile)
- [ ] Consistent spacing với variables

### i18n
- [ ] Tất cả text qua translation
- [ ] Support vi/en

### API Integration
- [ ] Config từ `/config` endpoint
- [ ] Products từ `/products` endpoint
- [ ] Banners từ `/banners` endpoint

---

## 7. Backend Settings (Admin)

Tất cả cấu hình được quản lý tại:
**Admin Panel → Modules → ZaloMiniapp → WebShop Settings**

| Field | Mô tả |
|-------|-------|
| `business_name` | Tên cửa hàng |
| `contact_email` | Email liên hệ |
| `contact_phone` | Số điện thoại |
| `hotline` | Hotline |
| `address` | Địa chỉ |
| `working_hours` | Giờ làm việc |
| `facebook_url` | Link Facebook |
| `instagram_url` | Link Instagram |
| `youtube_url` | Link YouTube |
| `tiktok_url` | Link TikTok |
| `zalo_url` | Link/SĐT Zalo |
| `flash_sale_enabled` | Bật/tắt Flash Sale |
| `flash_sale_title` | Tiêu đề Flash Sale |
| `flash_sale_end_time` | Thời gian kết thúc |
| `flash_sale_product_ids` | Danh sách sản phẩm sale |

---

## 8. Testing

### Verify không có hardcode

```bash
# Tìm hardcode potential
grep -r "0347\|thienvanyen\|Thiên Vân" webshop/src/
grep -r "#004D43\|#D4AF37" webshop/src/themes/*/components/
```

### Verify data từ API

1. Mở DevTools → Network
2. Kiểm tra request `GET /api/webshop/config`
3. Verify tất cả data hiển thị match với response

---

## 9. Ví dụ Flow

```
Admin Settings (Database)
        ↓
WebshopSettings Entity (Laravel)
        ↓
GET /api/webshop/config
        ↓
ThemeProvider.tsx (fetch config)
        ↓
useSiteConfig() hook
        ↓
Components (Header, Footer, etc.)
        ↓
UI Display
```

---

**Nguyên tắc vàng**: Nếu cần thay đổi bất kỳ thông tin nào hiển thị trên WebShop, **PHẢI** thay đổi qua Admin Settings, không được sửa code.
