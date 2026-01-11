---
description: Hướng dẫn Style UltimatePOS - Chuẩn UI/UX cho tất cả các trang
---

# Hướng dẫn Style UltimatePOS

Tài liệu này mô tả chuẩn UI/UX cho tất cả các trang trong hệ thống UltimatePOS, bao gồm Core và các Module.

---

## ⚠️ NGUYÊN TẮC QUAN TRỌNG NHẤT

### Layout phải COMPACT và HIỆN ĐẠI:
1. **KHÔNG được thừa không gian trống** - Mọi phần tử phải có mục đích
2. **Cards cùng hàng phải cùng chiều cao** - Sử dụng flexbox/grid tự động
3. **Padding vừa phải** - Không quá rộng, không quá hẹp
4. **Nội dung phải lấp đầy** - Không để card trống
5. **Responsive smart** - Mobile 1 cột, Tablet 2 cột, Desktop 3-4 cột

### Ví dụ Layout Đúng:
```
┌─────────────┬─────────────┬─────────────┐
│ Card 1      │ Card 2      │ Card 3      │  <- Cùng chiều cao
│ Nội dung    │ Nội dung    │ Nội dung    │
│ đầy đủ      │ đầy đủ      │ đầy đủ      │
└─────────────┴─────────────┴─────────────┘
┌───────────────────────────────────────────┐
│ Table/Content Full Width                  │
└───────────────────────────────────────────┘
```

### Ví dụ Layout SAI (Không được làm):
```
┌─────────────┬─────────────┬─────────────┐
│ Card 1      │ Card 2      │ Card 3      │
│ Nội dung    │             │ Nội dung    │  <- Card 2 trống!
│ nhiều       │   TRỐNG     │ ít          │  <- Chiều cao không đều!
│ dòng        │             │             │
└─────────────┴─────────────┴─────────────┘
```

---

## ⛔ QUY ĐỊNH VỀ MÀU NỀN HEADER

### KHÔNG SỬ DỤNG NỀN XANH GRADIENT CHO HEADER
1. **Loại bỏ hoàn toàn** nền gradient xanh (`tw-bg-gradient-to-r tw-from-primary-800 tw-to-primary-900`)
2. **Sử dụng nền trắng/trong suốt** thay thế
3. **Tiêu đề và mô tả** sử dụng màu tối:
   - Tiêu đề: `tw-text-gray-900`
   - Mô tả: `tw-text-gray-500`
4. **Icon có thể dùng màu nhấn**: `tw-text-sky-500`, `tw-text-green-500`, etc.

### Header Module chuẩn:
```html
<!-- Header KHÔNG có nền xanh -->
<div class="tw-px-5 tw-py-4">
    <div class="sm:tw-flex sm:tw-items-center sm:tw-justify-between">
        <div>
            <h1 class="tw-text-2xl md:tw-text-3xl tw-font-semibold tw-text-gray-900">
                <i class="fa fa-icon tw-text-sky-500"></i> Tên Module
            </h1>
            <p class="tw-text-gray-500 tw-mt-1">Mô tả module</p>
        </div>
        <div class="tw-mt-4 sm:tw-mt-0 tw-flex tw-gap-2">
            <!-- Buttons -->
        </div>
    </div>
</div>
```

---

## 📐 QUY ĐỊNH VỀ LAYOUT GRID

### Tối đa 4 cột trên 1 hàng
1. **Stats Cards**: Tối đa 4 cột trên 1 hàng
2. **Filter Form**: Tối đa 3-4 cột cho các input filter
3. **Action Buttons**: Tách riêng dưới filter, không nằm cùng hàng

### Filter Form chuẩn (3-4 cột với bo tròn BẮT BUỘC):

**⚠️ TẤT CẢ form elements PHẢI có bo tròn `border-radius: 8px`**

```html
<!-- Filter - Grid 4 cột với bo tròn -->
<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; align-items: end;">
    <div>
        <label class="tw-block tw-text-xs tw-font-medium tw-text-gray-500 tw-uppercase tw-mb-1">Trạng thái</label>
        <select style="width: 100%; height: 40px; padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 8px; background-color: white; font-size: 14px;">
            <option value="">Tất cả trạng thái</option>
        </select>
    </div>
    <div>
        <label class="tw-block tw-text-xs tw-font-medium tw-text-gray-500 tw-uppercase tw-mb-1">Từ ngày</label>
        <input type="date" style="width: 100%; height: 40px; padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px;">
    </div>
    <div>
        <label class="tw-block tw-text-xs tw-font-medium tw-text-gray-500 tw-uppercase tw-mb-1">Đến ngày</label>
        <input type="date" style="width: 100%; height: 40px; padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px;">
    </div>
    <div>
        <button class="tw-dw-btn tw-dw-btn-primary tw-text-white" style="width: 100%; height: 40px; border-radius: 8px;">
            <i class="fa fa-filter"></i> Lọc
        </button>
    </div>
</div>
```

### Form Elements - Bo tròn BẮT BUỘC:
| Element | Style bắt buộc |
|---------|----------------|
| `<select>` | `border-radius: 8px` |
| `<input>` | `border-radius: 8px` |
| `<button>` | `border-radius: 8px` |
| `<textarea>` | `border-radius: 8px` |
| Cards | `tw-rounded-xl` (12px) |

---

## 🔗 QUY ĐỊNH VỀ MENU NGANG MODULE

### Menu ngang phải có margin-top để không dính topbar:
```html
<div class="tw-bg-white tw-shadow-sm tw-mb-4 tw-rounded-xl tw-ring-1 tw-ring-gray-200 tw-mx-4" style="margin-top: 16px;">
    <nav class="tw-flex tw-flex-wrap tw-gap-1 tw-p-2 tw-overflow-x-auto">
        <!-- Menu items -->
    </nav>
</div>
```

### Active state sử dụng inline style (đảm bảo hiển thị đúng):
```html
<a href="..." 
   class="tw-inline-flex tw-items-center tw-px-4 tw-py-2 tw-rounded-lg tw-text-sm tw-font-medium"
   style="{{ $isActive ? 'background-color: #1f2937; color: #ffffff;' : 'color: #4b5563;' }}">
    Menu Item
</a>
```

---

## 1. Framework CSS

Sử dụng **TailwindCSS với prefix `tw-`** cho tất cả các class.

```html
<!-- Đúng -->
<div class="tw-bg-white tw-rounded-xl tw-shadow-sm">

<!-- Sai - không dùng TailwindCSS thuần -->
<div class="bg-white rounded-xl shadow-sm">
```


## 2. Layout Cơ bản

### 2.1 Header KHÔNG có nền xanh ⛔

**QUAN TRỌNG**: Header CHỈ chứa tiêu đề và nút actions. KHÔNG sử dụng nền gradient xanh.

```html
<!-- Header KHÔNG có nền xanh - Sử dụng nền trắng/trong suốt -->
<div class="tw-px-5 tw-py-4">
    <div class="sm:tw-flex sm:tw-items-center sm:tw-justify-between">
        <div>
            <h1 class="tw-text-2xl md:tw-text-3xl tw-font-semibold tw-text-gray-900">
                <i class="fa fa-icon tw-text-sky-500"></i> Tiêu đề trang
            </h1>
            <p class="tw-text-gray-500 tw-mt-1">Mô tả ngắn</p>
        </div>
        
        <!-- Nút Actions (bên phải) -->
        <div class="tw-mt-4 sm:tw-mt-0 tw-flex tw-gap-2">
            <a href="#" class="tw-inline-flex tw-items-center tw-gap-2 tw-px-4 tw-py-2 tw-bg-sky-500 tw-text-white tw-rounded-lg tw-font-medium hover:tw-bg-sky-600 tw-shadow-sm">
                <i class="fa fa-plus"></i> Thêm mới
            </a>
            <a href="#" class="tw-inline-flex tw-items-center tw-gap-2 tw-px-4 tw-py-2 tw-bg-white tw-text-gray-700 tw-rounded-lg tw-font-medium tw-ring-1 tw-ring-gray-200 hover:tw-bg-gray-50">
                <i class="fa fa-filter"></i> Bộ lọc
            </a>
        </div>
    </div>
</div>
```

### 2.2 Stats Cards (Nằm trong Content Area)

Stats Cards đặt trong Content Area:

```html
<!-- Content Area - Stats Cards đặt ở đây -->
<div class="tw-px-5 tw-py-4">
    <!-- Stats Cards - 4 cột -->
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
        <!-- Card 1 -->
        <div class="tw-bg-white tw-rounded-xl tw-p-4 tw-shadow-sm tw-ring-1 tw-ring-gray-200">
            <!-- Nội dung card -->
        </div>
        <!-- Card 2, 3, 4... -->
    </div>
</div>
```

### 2.3 Content Area


## 3. Stat Cards (Thẻ thống kê)

### 3.1 Card với Icon tròn

```html
<div class="tw-transition-all tw-duration-200 tw-bg-white tw-shadow-sm hover:tw-shadow-md tw-rounded-xl hover:tw--translate-y-0.5 tw-ring-1 tw-ring-gray-200">
    <div class="tw-p-4 sm:tw-p-5">
        <div class="tw-flex tw-items-center tw-gap-4">
            <!-- Icon tròn với màu -->
            <div class="tw-inline-flex tw-items-center tw-justify-center tw-w-10 tw-h-10 tw-rounded-full sm:tw-w-12 sm:tw-h-12 tw-shrink-0 tw-bg-sky-100 tw-text-sky-500">
                <i class="fa fa-boxes tw-text-xl"></i>
            </div>
            
            <!-- Nội dung -->
            <div class="tw-flex-1 tw-min-w-0">
                <p class="tw-text-sm tw-font-medium tw-text-gray-500 tw-truncate">Tiêu đề</p>
                <p class="tw-mt-0.5 tw-text-gray-900 tw-text-xl tw-font-semibold tw-tracking-tight tw-font-mono">
                    Giá trị
                </p>
            </div>
        </div>
    </div>
</div>
```

### 3.2 Màu sắc Icon phổ biến

| Loại | Background | Text Color |
|------|------------|------------|
| Primary/Info | `tw-bg-sky-100` | `tw-text-sky-500` |
| Success | `tw-bg-green-100` | `tw-text-green-500` |
| Warning | `tw-bg-yellow-100` | `tw-text-yellow-500` |
| Danger | `tw-bg-red-100` | `tw-text-red-500` |
| Purple | `tw-bg-purple-100` | `tw-text-purple-500` |
| Orange | `tw-bg-orange-100` | `tw-text-orange-500` |

## 4. Content Cards (Thẻ nội dung)

### 4.1 Card với Header Icon

```html
<div class="tw-transition-all tw-duration-200 tw-bg-white tw-shadow-sm tw-rounded-xl tw-ring-1 hover:tw-shadow-md hover:tw--translate-y-0.5 tw-ring-gray-200">
    <div class="tw-p-4 sm:tw-p-5">
        <!-- Header -->
        <div class="tw-flex tw-items-center tw-gap-2.5">
            <div class="tw-border-2 tw-flex tw-items-center tw-justify-center tw-rounded-full tw-w-10 tw-h-10">
                <i class="fa fa-chart-line tw-text-sky-500"></i>
            </div>
            <h3 class="tw-font-bold tw-text-base lg:tw-text-xl">Tiêu đề Card</h3>
        </div>
        
        <!-- Content -->
        <div class="tw-mt-5">
            <!-- Nội dung card -->
        </div>
    </div>
</div>
```

### 4.2 Card Full Width (span 2 columns)

```html
<div class="tw-transition-all lg:tw-col-span-2 xl:tw-col-span-2 tw-duration-200 tw-bg-white tw-shadow-sm tw-rounded-xl tw-ring-1 hover:tw-shadow-md hover:tw--translate-y-0.5 tw-ring-gray-200">
    <!-- Content -->
</div>
```

## 5. Buttons

### 5.1 Primary Button

```html
<button class="tw-dw-btn tw-dw-btn-primary tw-text-white">
    <i class="fa fa-save tw-mr-1"></i> Lưu
</button>
```

### 5.2 Success Button

```html
<button class="tw-dw-btn tw-dw-btn-success tw-text-white">
    <i class="fa fa-download tw-mr-1"></i> Xuất
</button>
```

### 5.3 White Button (trên nền tối)

```html
<button class="tw-inline-flex tw-items-center tw-gap-1 tw-px-3 tw-py-2 tw-text-sm tw-font-medium tw-text-gray-900 tw-bg-white tw-rounded-lg hover:tw-bg-primary-50">
    <i class="fa fa-filter"></i> Lọc
</button>
```

## 6. Inputs

### 6.1 Input trên nền tối (header)

```html
<input type="date" class="tw-px-3 tw-py-2 tw-text-sm tw-font-medium tw-text-gray-900 tw-bg-white tw-rounded-lg">
```

### 6.2 Input trong card

Sử dụng class Bootstrap chuẩn:
```html
<input type="text" class="form-control">
<select class="form-control select2">
```

## 7. Tables

### 7.1 Table trong Card

```html
<div class="tw-flow-root tw-mt-5">
    <table class="table table-bordered table-striped" style="width: 100%;">
        <thead>
            <tr>
                <th>Cột 1</th>
                <th class="text-right">Cột 2</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Giá trị</td>
                <td class="text-right tw-font-semibold">@format_currency($amount)</td>
            </tr>
        </tbody>
    </table>
</div>
```

## 8. Labels/Badges

```html
<!-- Badge màu -->
<span class="tw-inline-flex tw-items-center tw-px-2 tw-py-1 tw-rounded-full tw-text-xs tw-font-medium tw-bg-green-100 tw-text-green-700">
    Thành công
</span>

<span class="tw-inline-flex tw-items-center tw-px-2 tw-py-1 tw-rounded-full tw-text-xs tw-font-medium tw-bg-orange-100 tw-text-orange-700">
    Đang xử lý
</span>

<span class="tw-inline-flex tw-items-center tw-px-2 tw-py-1 tw-rounded-full tw-text-xs tw-font-medium tw-bg-red-100 tw-text-red-700">
    Thất bại
</span>
```

## 9. Charts Container

```html
<div class="tw-w-full tw-border tw-border-gray-200 tw-border-dashed tw-rounded-xl tw-bg-gray-50 tw-p-4">
    <div style="height: 300px;">
        <canvas id="chartId"></canvas>
    </div>
</div>
```

## 10. Grid Responsive

| Screen | Prefix | Columns |
|--------|--------|---------|
| Mobile | (none) | 1 column |
| Small (640px+) | `sm:` | 2 columns |
| Large (1024px+) | `lg:` | 2 columns |
| XLarge (1280px+) | `xl:` | 4 columns |

```html
<div class="tw-grid tw-grid-cols-1 tw-gap-4 sm:tw-grid-cols-2 xl:tw-grid-cols-4 sm:tw-gap-5">
```

## 11. Transition & Animation

Luôn thêm transition cho hover effects:

```html
class="tw-transition-all tw-duration-200 hover:tw-shadow-md hover:tw--translate-y-0.5"
```

## 12. Ring Border

Sử dụng ring thay vì border thường:

```html
class="tw-ring-1 tw-ring-gray-200"
```

## 13. Text Colors

| Mục đích | Class |
|----------|-------|
| Title/Heading | `tw-text-gray-900` hoặc `tw-font-bold` |
| Label | `tw-text-gray-500` |
| Muted/Helper | `tw-text-gray-400` |
| Success value | `tw-text-green-600` |
| Danger value | `tw-text-red-600` |
| Warning value | `tw-text-yellow-600` |

## 14. Font

- Tiêu đề: `tw-font-bold` hoặc `tw-font-semibold`
- Số tiền/Giá trị: `tw-font-mono tw-font-semibold`
- Text thường: Mặc định

## 15. Spacing

- Padding card: `tw-p-4 sm:tw-p-5`
- Gap giữa cards: `tw-gap-4 sm:tw-gap-5`
- Margin top content: `tw-mt-5`
- Section padding: `tw-px-5 tw-py-6`

## 16. Ví dụ Template Hoàn chỉnh

```blade
@extends('layouts.app')

@section('title', 'Tiêu đề trang')

@section('content')
@include('modulename::layouts.nav')

<!-- Header KHÔNG có nền xanh -->
<div class="tw-px-5 tw-py-4">
    <div class="sm:tw-flex sm:tw-items-center sm:tw-justify-between">
        <div>
            <h1 class="tw-text-2xl md:tw-text-3xl tw-font-semibold tw-text-gray-900">
                <i class="fa fa-icon tw-text-sky-500"></i> Tiêu đề trang
            </h1>
            <p class="tw-text-gray-500 tw-mt-1">Mô tả ngắn về module</p>
        </div>
        <div class="tw-mt-4 sm:tw-mt-0 tw-flex tw-gap-2">
            <!-- Buttons -->
        </div>
    </div>
</div>

<!-- Stats Row -->
<div class="tw-px-5 tw-pb-4">
    <div class="tw-grid tw-grid-cols-1 tw-gap-4 sm:tw-grid-cols-2 xl:tw-grid-cols-4 sm:tw-gap-5">
        <!-- Stat Cards -->
    </div>
</div>

<!-- Main Content -->
<div class="tw-px-5 tw-py-6">
    <div class="tw-grid tw-grid-cols-1 tw-gap-4 sm:tw-gap-5 lg:tw-grid-cols-2">
        <!-- Content Cards -->
    </div>
</div>
@endsection
```

---

**LƯU Ý QUAN TRỌNG:**
1. ⛔ **KHÔNG sử dụng nền gradient xanh** cho header (`tw-bg-gradient-to-r tw-from-primary-800 tw-to-primary-900` - BỊ CẤM)
2. ✅ **BẮT BUỘC bo tròn** cho tất cả form elements: `select`, `input`, `button`, `textarea` với `border-radius: 8px`
3. ✅ **Dùng inline style cho grid layout** nếu Tailwind không hoạt động: `style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;"`
4. KHÔNG sử dụng AdminLTE boxes (box, box-header, etc.) - thay bằng card style mới
5. Luôn test responsive trên mobile
6. Giữ nhất quán màu sắc theo bảng ở trên
7. Sử dụng Icons từ FontAwesome 5+ (fa fa-xxx hoặc fas fa-xxx)
8. Cards sử dụng `tw-rounded-xl` (12px), form elements dùng `border-radius: 8px`

