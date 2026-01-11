---
description: Hướng dẫn viết Module Laravel chuẩn - Tránh lỗi Migration và Column
---

# /module - Module Development Guide

## 🚨 CRITICAL: Tránh lỗi "Column not found" trong Module

### Vấn đề thường gặp

```
SQLSTATE[42S22]: Column not found: 1054 Unknown column 'xyz_settings' in 'SELECT'
```

**Nguyên nhân:**
- Module thêm column vào Core tables (`business`, `contacts`, `users`, `transactions`) nhưng migration chưa chạy hoặc thiếu
- Code truy cập column trước khi migration được thực thi
- Không có fallback khi column không tồn tại

---

## ✅ CHECKLIST: Module Migration Standards

### 1. Luôn dùng `hasTable()` và `hasColumn()` checks

```php
// ✅ ĐÚNG - Tạo bảng mới
if (!Schema::hasTable('crm_customers')) {
    Schema::create('crm_customers', function (Blueprint $table) {
        // ...
    });
}

// ✅ ĐÚNG - Thêm column vào bảng Core
if (!Schema::hasColumn('business', 'crm_settings')) {
    Schema::table('business', function (Blueprint $table) {
        $table->json('crm_settings')->nullable()->after('pos_settings');
    });
}

// ❌ SAI - Không check trước
Schema::table('business', function (Blueprint $table) {
    $table->json('crm_settings')->nullable();
});
```

### 2. Tách migration riêng cho Core tables

```
Modules/YourModule/Database/Migrations/
├── 2024_01_01_000001_create_yourmodule_tables.php      # Module tables
├── 2024_01_01_000002_add_yourmodule_to_business.php    # Core: business
├── 2024_01_01_000003_add_yourmodule_to_contacts.php    # Core: contacts
└── 2024_01_01_000004_add_yourmodule_to_transactions.php # Core: transactions
```

### 3. Code phải handle khi column chưa tồn tại

```php
// ✅ ĐÚNG - Safe query với try-catch
public function getSettings()
{
    try {
        return Business::where('id', $this->business_id)
            ->value('crm_settings');
    } catch (\Exception $e) {
        // Column not found - return default
        return null;
    }
}

// ✅ ĐÚNG - Check với Schema before query
public function getSettings()
{
    if (!Schema::hasColumn('business', 'crm_settings')) {
        return [];
    }
    
    $settings = Business::where('id', $this->business_id)
        ->value('crm_settings');
    
    return $settings ? json_decode($settings, true) : [];
}

// ❌ SAI - Query trực tiếp không có fallback
public function getSettings()
{
    return Business::where('id', $this->business_id)
        ->value('crm_settings'); // FAIL nếu column chưa có!
}
```

### 4. ServiceProvider: Check dependencies

```php
// Modules/YourModule/Providers/YourModuleServiceProvider.php

public function boot()
{
    // Check required columns exist before registering
    if (!$this->checkDatabaseReady()) {
        return;
    }
    
    // Register routes, views, etc.
}

private function checkDatabaseReady(): bool
{
    try {
        return Schema::hasColumn('business', 'yourmodule_settings');
    } catch (\Exception $e) {
        return false;
    }
}
```

---

## 📁 Module Structure Template

```
Modules/YourModule/
├── Config/
│   └── config.php
├── Database/
│   ├── Migrations/
│   │   ├── 2024_01_01_000001_create_yourmodule_tables.php
│   │   └── 2024_01_01_000002_add_yourmodule_settings_to_core.php
│   └── Seeders/
│       └── YourModuleDatabaseSeeder.php
├── Entities/
│   └── YourModel.php
├── Http/
│   ├── Controllers/
│   └── Middleware/
├── Providers/
│   └── YourModuleServiceProvider.php
├── Resources/
│   ├── lang/
│   └── views/
├── Routes/
│   └── web.php
├── module.json
└── composer.json
```

---

## 🔧 Migration Template

```php
<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Add YourModule settings to business table
 * 
 * This migration safely adds columns to CORE tables.
 * Uses hasColumn checks for idempotent execution.
 */
return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        // Add settings column to business table
        if (!Schema::hasColumn('business', 'yourmodule_settings')) {
            Schema::table('business', function (Blueprint $table) {
                $table->json('yourmodule_settings')->nullable()->after('pos_settings');
            });
        }
        
        // Add columns to contacts if needed
        if (!Schema::hasColumn('contacts', 'yourmodule_data')) {
            Schema::table('contacts', function (Blueprint $table) {
                $table->json('yourmodule_data')->nullable();
            });
        }
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        if (Schema::hasColumn('business', 'yourmodule_settings')) {
            Schema::table('business', function (Blueprint $table) {
                $table->dropColumn('yourmodule_settings');
            });
        }
        
        if (Schema::hasColumn('contacts', 'yourmodule_data')) {
            Schema::table('contacts', function (Blueprint $table) {
                $table->dropColumn('yourmodule_data');
            });
        }
    }
};
```

---

## 🎯 Quick Fixes for Common Errors

### Error: Column not found

```bash
# 1. Check if migration exists
ls Modules/YourModule/Database/Migrations/

# 2. Run module migrations
php artisan module:migrate YourModule

# 3. If still fails, run all migrations
php artisan migrate

# 4. Check migration status
php artisan migrate:status | grep yourmodule
```

### Error: Table doesn't exist

```bash
# Check if module is enabled
php artisan module:list

# Enable module
php artisan module:enable YourModule

# Run migrations
php artisan module:migrate YourModule
```

---

## 📝 Commit Checklist for Modules

Before committing module changes:

- [ ] All new tables use `if (!Schema::hasTable())` checks
- [ ] All new columns in core tables use `if (!Schema::hasColumn())` checks
- [ ] down() method mirrors up() with proper existence checks
- [ ] Code accessing new columns has try-catch or column existence checks
- [ ] Run `php artisan migrate:fresh --seed` to test clean install
- [ ] Run `php artisan migrate` to test upgrade scenario
- [ ] Test with module disabled then enabled

---

## 🛡️ Core Tables Registry

When adding columns to these tables, ALWAYS use existence checks:

| Table | Module Usage |
|-------|--------------|
| `business` | Settings JSON per module |
| `contacts` | Customer/Supplier data |
| `transactions` | Order/Invoice extra fields |
| `users` | User module-specific data |
| `products` | Product extensions |
| `variations` | Variant extensions |

---

**Author**: Bizino AI DEV  
**Last Updated**: 2026-01-02