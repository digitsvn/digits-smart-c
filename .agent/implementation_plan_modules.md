# Kế Hoạch Triển Khai 3 Modules: Affiliate, CRM, Loyalty

## Tổng Quan
Dự án xây dựng 3 module độc lập trên nền tảng UltimatePOS v6.10, tuân thủ chuẩn `nwidart/laravel-modules`.

---

## Phân Tích Hệ Thống Hiện Có

### Bảng Core Quan Trọng
- `contacts` - Khách hàng/Nhà cung cấp (Model: `App\Contact`)
- `users` - Người dùng hệ thống (Model: `App\User`)
- `transactions` - Giao dịch bán hàng
- `transaction_payments` - Thanh toán
- `business` - Thông tin doanh nghiệp

### Module Tham Khảo Có Sẵn
- `Modules/Dev/LoyaltyCard` - Tham khảo hệ thống điểm
- `Modules/Crm` - Module CRM hiện có (cần kiểm tra và mở rộng)

---

## Module 1: AFFILIATE (Tiếp thị liên kết)

### 1.1 Database Schema

```sql
-- Bảng đối tác affiliate
CREATE TABLE affiliate_partners (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    contact_id INT UNSIGNED NULL,  -- Liên kết với contacts
    user_id INT UNSIGNED NULL,     -- Liên kết với users (nếu có tài khoản)
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    referral_code VARCHAR(50) UNIQUE NOT NULL,
    partner_type ENUM('referrer', 'kol', 'strategic') DEFAULT 'referrer',
    tier_id BIGINT UNSIGNED NULL,
    bank_name VARCHAR(255),
    bank_account_number VARCHAR(100),
    bank_account_name VARCHAR(255),
    total_earnings DECIMAL(22,4) DEFAULT 0,
    pending_balance DECIMAL(22,4) DEFAULT 0,
    available_balance DECIMAL(22,4) DEFAULT 0,
    status ENUM('pending', 'active', 'suspended') DEFAULT 'pending',
    created_by INT UNSIGNED,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    FOREIGN KEY (business_id) REFERENCES business(id),
    INDEX (referral_code),
    INDEX (business_id)
);

-- Bảng cấp bậc affiliate
CREATE TABLE affiliate_tiers (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    name VARCHAR(100) NOT NULL,
    min_revenue DECIMAL(22,4) DEFAULT 0,
    commission_rate DECIMAL(5,2) NOT NULL,  -- Phần trăm hoa hồng
    color VARCHAR(20),
    sort_order INT DEFAULT 0,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Bảng hoa hồng
CREATE TABLE affiliate_commissions (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    partner_id BIGINT UNSIGNED NOT NULL,
    transaction_id INT UNSIGNED NOT NULL,
    order_amount DECIMAL(22,4) NOT NULL,
    commission_rate DECIMAL(5,2) NOT NULL,
    commission_amount DECIMAL(22,4) NOT NULL,
    status ENUM('pending', 'approved', 'paid', 'cancelled') DEFAULT 'pending',
    approved_by INT UNSIGNED NULL,
    approved_at TIMESTAMP NULL,
    paid_at TIMESTAMP NULL,
    notes TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (partner_id) REFERENCES affiliate_partners(id),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

-- Bảng yêu cầu rút tiền
CREATE TABLE affiliate_payouts (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    partner_id BIGINT UNSIGNED NOT NULL,
    amount DECIMAL(22,4) NOT NULL,
    status ENUM('pending', 'processing', 'completed', 'rejected') DEFAULT 'pending',
    bank_name VARCHAR(255),
    bank_account_number VARCHAR(100),
    bank_account_name VARCHAR(255),
    processed_by INT UNSIGNED NULL,
    processed_at TIMESTAMP NULL,
    rejection_reason TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Bảng tracking clicks
CREATE TABLE affiliate_clicks (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    partner_id BIGINT UNSIGNED NOT NULL,
    referral_code VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    referrer_url TEXT,
    landing_page TEXT,
    device_type VARCHAR(20),
    converted BOOLEAN DEFAULT FALSE,
    conversion_id BIGINT UNSIGNED NULL,
    created_at TIMESTAMP,
    INDEX (referral_code),
    INDEX (partner_id),
    INDEX (created_at)
);

-- Bảng cấu hình affiliate
CREATE TABLE affiliate_settings (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL UNIQUE,
    is_enabled BOOLEAN DEFAULT TRUE,
    cookie_duration INT DEFAULT 30,  -- Ngày
    auto_approve_commission BOOLEAN DEFAULT FALSE,
    min_payout_amount DECIMAL(22,4) DEFAULT 100000,
    payout_schedule ENUM('weekly', 'biweekly', 'monthly') DEFAULT 'monthly',
    terms_and_conditions TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 1.2 Cấu Trúc Module

```
Modules/Affiliate/
├── Config/config.php
├── Database/
│   └── Migrations/
│       ├── 2024_01_01_create_affiliate_partners_table.php
│       ├── 2024_01_02_create_affiliate_tiers_table.php
│       ├── 2024_01_03_create_affiliate_commissions_table.php
│       ├── 2024_01_04_create_affiliate_payouts_table.php
│       ├── 2024_01_05_create_affiliate_clicks_table.php
│       └── 2024_01_06_create_affiliate_settings_table.php
├── Entities/
│   ├── AffiliatePartner.php
│   ├── AffiliateTier.php
│   ├── AffiliateCommission.php
│   ├── AffiliatePayout.php
│   └── AffiliateClick.php
├── Http/
│   ├── Controllers/
│   │   ├── AffiliateController.php        -- Quản lý đối tác
│   │   ├── CommissionController.php       -- Quản lý hoa hồng
│   │   ├── PayoutController.php           -- Quản lý rút tiền
│   │   ├── TierController.php             -- Quản lý cấp bậc
│   │   ├── SettingsController.php         -- Cài đặt
│   │   ├── TrackingController.php         -- Tracking link
│   │   └── DataController.php             -- Module integration
│   └── Middleware/
│       └── TrackAffiliate.php             -- Middleware bắt referral
├── Services/
│   ├── AffiliateService.php               -- Logic nghiệp vụ
│   └── CommissionCalculator.php           -- Tính toán hoa hồng
├── Events/
│   └── AffiliateConversion.php
├── Listeners/
│   └── ProcessAffiliateConversion.php
├── Resources/
│   ├── views/
│   │   ├── partners/
│   │   ├── commissions/
│   │   ├── payouts/
│   │   └── settings/
│   └── lang/vi/
└── Routes/
    ├── web.php
    └── api.php
```

### 1.3 Tính Năng Chính
1. **Dashboard Affiliate** - Thống kê tổng quan
2. **Quản lý đối tác** - CRUD, phê duyệt
3. **Quản lý hoa hồng** - Xem, duyệt, thanh toán
4. **Quản lý rút tiền** - Xử lý yêu cầu
5. **Tracking** - Link giới thiệu, thống kê clicks
6. **Tự động nâng cấp tier** - Dựa trên doanh thu

---

## Module 2: CRM (Quản lý quan hệ khách hàng)

### 2.1 Database Schema

```sql
-- Mở rộng contacts với thông tin CRM
CREATE TABLE crm_customer_profiles (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    contact_id INT UNSIGNED NOT NULL UNIQUE,
    
    -- RFM Scores
    rfm_recency_score INT DEFAULT 0,
    rfm_frequency_score INT DEFAULT 0,
    rfm_monetary_score INT DEFAULT 0,
    rfm_total_score INT DEFAULT 0,
    rfm_segment VARCHAR(50),  -- 'champion', 'loyal', 'potential', 'at_risk', etc.
    
    -- Health Score
    health_score INT DEFAULT 50,  -- 0-100
    health_status ENUM('excellent', 'good', 'average', 'poor', 'critical') DEFAULT 'average',
    
    -- Thống kê
    total_orders INT DEFAULT 0,
    total_spent DECIMAL(22,4) DEFAULT 0,
    average_order_value DECIMAL(22,4) DEFAULT 0,
    first_order_date DATE,
    last_order_date DATE,
    days_since_last_order INT DEFAULT 0,
    
    -- Thông tin bổ sung
    customer_since DATE,
    birthday DATE,
    notes TEXT,
    tags JSON,
    custom_fields JSON,
    
    last_rfm_calculated_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    INDEX (rfm_segment),
    INDEX (health_status),
    INDEX (business_id)
);

-- Lịch sử tương tác
CREATE TABLE crm_interactions (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    contact_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,  -- Nhân viên
    type ENUM('call', 'email', 'meeting', 'note', 'task', 'sms', 'other') NOT NULL,
    subject VARCHAR(255),
    description TEXT,
    outcome VARCHAR(100),
    scheduled_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    INDEX (contact_id),
    INDEX (type)
);

-- Pipeline deals (B2B)
CREATE TABLE crm_pipelines (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE crm_pipeline_stages (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    pipeline_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(20),
    probability INT DEFAULT 0,  -- 0-100%
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE crm_deals (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    contact_id INT UNSIGNED NOT NULL,
    pipeline_id BIGINT UNSIGNED NOT NULL,
    stage_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    value DECIMAL(22,4),
    expected_close_date DATE,
    assigned_to INT UNSIGNED,
    status ENUM('open', 'won', 'lost') DEFAULT 'open',
    lost_reason TEXT,
    notes TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    INDEX (contact_id),
    INDEX (stage_id),
    INDEX (status)
);

-- Automation rules
CREATE TABLE crm_automation_rules (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    trigger_type VARCHAR(50) NOT NULL,  -- 'segment_change', 'order_completed', 'birthday', etc.
    trigger_condition JSON,
    action_type VARCHAR(50) NOT NULL,   -- 'send_email', 'send_sms', 'assign_tag', etc.
    action_config JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Email campaigns
CREATE TABLE crm_email_templates (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    variables JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE crm_campaigns (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    type ENUM('email', 'sms') DEFAULT 'email',
    template_id BIGINT UNSIGNED NULL,
    segment_filter JSON,  -- Điều kiện lọc khách hàng
    scheduled_at TIMESTAMP NULL,
    sent_at TIMESTAMP NULL,
    status ENUM('draft', 'scheduled', 'sending', 'sent', 'cancelled') DEFAULT 'draft',
    stats JSON,  -- sent, opened, clicked, etc.
    created_by INT UNSIGNED,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Cấu hình RFM
CREATE TABLE crm_rfm_settings (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL UNIQUE,
    recency_weight DECIMAL(3,2) DEFAULT 0.33,
    frequency_weight DECIMAL(3,2) DEFAULT 0.33,
    monetary_weight DECIMAL(3,2) DEFAULT 0.34,
    recency_thresholds JSON,   -- [30, 60, 90, 180, 365]
    frequency_thresholds JSON, -- [1, 3, 5, 10, 20]
    monetary_thresholds JSON,  -- [100000, 500000, 1000000, 5000000, 10000000]
    segment_definitions JSON,
    auto_calculate BOOLEAN DEFAULT TRUE,
    calculate_frequency ENUM('daily', 'weekly', 'monthly') DEFAULT 'daily',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 2.2 Cấu Trúc Module

```
Modules/CrmAdvanced/
├── Config/config.php
├── Database/Migrations/
├── Entities/
│   ├── CustomerProfile.php
│   ├── Interaction.php
│   ├── Pipeline.php
│   ├── PipelineStage.php
│   ├── Deal.php
│   ├── AutomationRule.php
│   ├── EmailTemplate.php
│   └── Campaign.php
├── Http/Controllers/
│   ├── CustomerController.php     -- Hồ sơ 360°
│   ├── InteractionController.php  -- Lịch sử tương tác
│   ├── PipelineController.php     -- Pipeline
│   ├── DealController.php         -- Deals B2B
│   ├── AutomationController.php   -- Quy tắc tự động
│   ├── CampaignController.php     -- Email marketing
│   ├── RfmController.php          -- Phân tích RFM
│   └── DataController.php
├── Services/
│   ├── RfmCalculator.php          -- Tính toán RFM
│   ├── HealthScoreCalculator.php  -- Tính điểm sức khỏe
│   ├── SegmentationService.php    -- Phân khúc tự động
│   └── AutomationEngine.php       -- Engine tự động hóa
├── Console/Commands/
│   └── CalculateRfmScores.php     -- Cronjob tính RFM
├── Events/
│   ├── CustomerSegmentChanged.php
│   └── OrderCompleted.php
└── Resources/views/
```

### 2.3 Công Thức RFM

```php
// Recency Score (1-5): Thời gian từ lần mua cuối
// - 1-30 ngày: 5 điểm
// - 31-60 ngày: 4 điểm
// - 61-90 ngày: 3 điểm
// - 91-180 ngày: 2 điểm
// - >180 ngày: 1 điểm

// Frequency Score (1-5): Số lần mua
// - >20 lần: 5 điểm
// - 10-20 lần: 4 điểm
// - 5-9 lần: 3 điểm
// - 2-4 lần: 2 điểm
// - 1 lần: 1 điểm

// Monetary Score (1-5): Tổng chi tiêu
// - >10M: 5 điểm
// - 5-10M: 4 điểm
// - 1-5M: 3 điểm
// - 500K-1M: 2 điểm
// - <500K: 1 điểm

// Segments dựa trên RFM:
// Champions: R=5, F≥4, M≥4
// Loyal: F≥4
// Potential Loyalists: R≥4, F≥2
// New Customers: R=5, F=1
// At Risk: R≤2, F≥3
// Can't Lose: R≤2, M≥4
// Hibernating: R=1, F=1
```

---

## Module 3: LOYALTY (Khách hàng thân thiết)

### 3.1 Database Schema

```sql
-- Hạng thành viên
CREATE TABLE loyalty_tiers (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    name VARCHAR(100) NOT NULL,
    min_points INT DEFAULT 0,       -- Điểm tối thiểu để đạt hạng
    points_multiplier DECIMAL(3,2) DEFAULT 1.00,  -- Hệ số nhân điểm
    discount_percent DECIMAL(5,2) DEFAULT 0,
    benefits TEXT,
    color VARCHAR(20),
    icon VARCHAR(50),
    sort_order INT DEFAULT 0,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Thành viên loyalty
CREATE TABLE loyalty_members (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    contact_id INT UNSIGNED NOT NULL UNIQUE,
    tier_id BIGINT UNSIGNED NOT NULL,
    member_code VARCHAR(50) UNIQUE,
    current_points INT DEFAULT 0,       -- Điểm khả dụng
    lifetime_points INT DEFAULT 0,      -- Tổng điểm tích lũy từ trước đến nay
    redeemed_points INT DEFAULT 0,      -- Điểm đã sử dụng
    tier_points INT DEFAULT 0,          -- Điểm tính tier (reset theo chu kỳ)
    tier_expiry_date DATE,
    status ENUM('active', 'suspended', 'expired') DEFAULT 'active',
    joined_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (tier_id) REFERENCES loyalty_tiers(id),
    INDEX (member_code),
    INDEX (tier_id)
);

-- Lịch sử điểm
CREATE TABLE loyalty_point_transactions (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    member_id BIGINT UNSIGNED NOT NULL,
    transaction_id INT UNSIGNED NULL,   -- Liên kết đơn hàng (nếu có)
    type ENUM('earn', 'redeem', 'expire', 'adjust', 'bonus') NOT NULL,
    points INT NOT NULL,                 -- Dương = cộng, Âm = trừ
    points_before INT NOT NULL,
    points_after INT NOT NULL,
    description VARCHAR(255),
    reference_type VARCHAR(50),          -- 'order', 'voucher', 'mission', 'wheel', etc.
    reference_id BIGINT UNSIGNED,
    expires_at TIMESTAMP NULL,
    created_by INT UNSIGNED,
    created_at TIMESTAMP,
    INDEX (member_id),
    INDEX (type),
    INDEX (created_at)
);

-- Vouchers
CREATE TABLE loyalty_vouchers (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type ENUM('percent', 'fixed', 'freeship') NOT NULL,
    value DECIMAL(22,4) NOT NULL,
    min_order_value DECIMAL(22,4) DEFAULT 0,
    max_discount DECIMAL(22,4) NULL,
    points_required INT DEFAULT 0,       -- Điểm cần để đổi
    quantity INT NULL,                   -- NULL = unlimited
    used_count INT DEFAULT 0,
    per_user_limit INT DEFAULT 1,
    tier_ids JSON,                       -- Hạng được phép sử dụng
    is_public BOOLEAN DEFAULT TRUE,
    starts_at TIMESTAMP,
    expires_at TIMESTAMP,
    status ENUM('active', 'inactive', 'expired') DEFAULT 'active',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Voucher đã đổi của member
CREATE TABLE loyalty_member_vouchers (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT UNSIGNED NOT NULL,
    voucher_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,           -- Mã riêng cho member
    status ENUM('available', 'used', 'expired') DEFAULT 'available',
    used_at TIMESTAMP NULL,
    used_transaction_id INT UNSIGNED NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    INDEX (member_id),
    INDEX (code)
);

-- Nhiệm vụ (Missions)
CREATE TABLE loyalty_missions (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,           -- 'first_purchase', 'review', 'birthday', 'referral', etc.
    condition_config JSON,               -- Điều kiện hoàn thành
    reward_type ENUM('points', 'voucher', 'badge') NOT NULL,
    reward_value INT,                    -- Số điểm hoặc voucher_id
    reward_voucher_id BIGINT UNSIGNED NULL,
    reward_badge_id BIGINT UNSIGNED NULL,
    is_repeatable BOOLEAN DEFAULT FALSE,
    max_completions INT DEFAULT 1,
    tier_ids JSON,
    is_active BOOLEAN DEFAULT TRUE,
    starts_at TIMESTAMP NULL,
    ends_at TIMESTAMP NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Tiến độ nhiệm vụ của member
CREATE TABLE loyalty_member_missions (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT UNSIGNED NOT NULL,
    mission_id BIGINT UNSIGNED NOT NULL,
    progress INT DEFAULT 0,              -- Tiến độ hiện tại
    target INT DEFAULT 1,                -- Mục tiêu
    completions INT DEFAULT 0,
    status ENUM('in_progress', 'completed', 'claimed') DEFAULT 'in_progress',
    completed_at TIMESTAMP NULL,
    claimed_at TIMESTAMP NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE KEY (member_id, mission_id)
);

-- Huy hiệu
CREATE TABLE loyalty_badges (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(255),
    criteria_type VARCHAR(50),           -- 'order_count', 'total_spent', 'mission', etc.
    criteria_value INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE loyalty_member_badges (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT UNSIGNED NOT NULL,
    badge_id BIGINT UNSIGNED NOT NULL,
    earned_at TIMESTAMP,
    created_at TIMESTAMP,
    UNIQUE KEY (member_id, badge_id)
);

-- Vòng quay may mắn
CREATE TABLE loyalty_wheel_configs (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    spin_cost INT DEFAULT 0,             -- Điểm để quay
    prizes JSON,                         -- [{name, type, value, probability, quantity}]
    tier_ids JSON,
    daily_limit INT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    starts_at TIMESTAMP NULL,
    ends_at TIMESTAMP NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE loyalty_wheel_spins (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT UNSIGNED NOT NULL,
    wheel_id BIGINT UNSIGNED NOT NULL,
    prize_index INT NOT NULL,
    prize_name VARCHAR(255),
    prize_value INT,
    created_at TIMESTAMP,
    INDEX (member_id),
    INDEX (created_at)
);

-- Cấu hình Loyalty
CREATE TABLE loyalty_settings (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    business_id INT UNSIGNED NOT NULL UNIQUE,
    is_enabled BOOLEAN DEFAULT TRUE,
    points_per_currency DECIMAL(10,4) DEFAULT 0.01,  -- VD: 1 điểm = 1000 VND
    currency_per_point DECIMAL(22,4) DEFAULT 1000,   -- Giá trị quy đổi
    points_expiry_months INT DEFAULT 12,
    tier_reset_months INT DEFAULT 12,
    auto_enroll BOOLEAN DEFAULT TRUE,
    welcome_points INT DEFAULT 0,
    birthday_points INT DEFAULT 0,
    referral_points INT DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 3.2 Cấu Trúc Module

```
Modules/Loyalty/
├── Config/config.php
├── Database/Migrations/
├── Entities/
│   ├── LoyaltyTier.php
│   ├── LoyaltyMember.php
│   ├── PointTransaction.php
│   ├── Voucher.php
│   ├── MemberVoucher.php
│   ├── Mission.php
│   ├── MemberMission.php
│   ├── Badge.php
│   ├── WheelConfig.php
│   └── WheelSpin.php
├── Http/Controllers/
│   ├── MemberController.php       -- Quản lý thành viên
│   ├── TierController.php         -- Quản lý hạng
│   ├── PointController.php        -- Điểm thưởng
│   ├── VoucherController.php      -- Vouchers
│   ├── MissionController.php      -- Nhiệm vụ
│   ├── BadgeController.php        -- Huy hiệu
│   ├── WheelController.php        -- Vòng quay
│   ├── SettingsController.php     -- Cài đặt
│   ├── RedeemController.php       -- Đổi thưởng
│   └── DataController.php
├── Services/
│   ├── PointsService.php          -- Xử lý điểm
│   ├── TierService.php            -- Nâng/hạ tier
│   ├── VoucherService.php         -- Voucher logic
│   ├── MissionService.php         -- Mission tracking
│   └── WheelService.php           -- Vòng quay
├── Events/
│   ├── PointsEarned.php
│   ├── PointsRedeemed.php
│   ├── TierChanged.php
│   └── MissionCompleted.php
└── Resources/views/
```

---

## Luồng Tích Hợp (Integration Flow)

### Event Listeners (trong EventServiceProvider core hoặc module)

```php
// Khi đơn hàng hoàn thành (transactions.status = 'final')
Event::listen(OrderCompleted::class, function ($event) {
    $transaction = $event->transaction;
    
    // 1. Loyalty: Tính và cộng điểm
    app(PointsService::class)->earnFromOrder($transaction);
    
    // 2. CRM: Cập nhật RFM
    app(RfmCalculator::class)->updateForContact($transaction->contact_id);
    
    // 3. Affiliate: Tính hoa hồng (nếu có referrer)
    app(CommissionCalculator::class)->processOrder($transaction);
});
```

### Middleware TrackAffiliate

```php
// Đặt trong Http Kernel hoặc specific routes
public function handle($request, Closure $next)
{
    if ($code = $request->query('ref')) {
        Cookie::queue('affiliate_code', $code, 60 * 24 * 30); // 30 ngày
        
        // Log click
        AffiliateClick::create([
            'referral_code' => $code,
            'ip_address' => $request->ip(),
            'user_agent' => $request->userAgent(),
            // ...
        ]);
    }
    
    return $next($request);
}
```

---

## Thứ Tự Triển Khai

### Phase 1: Foundation (Tuần 1-2)
1. Tạo cấu trúc 3 modules theo chuẩn nwidart
2. Chạy migrations
3. Tạo Models/Entities cơ bản
4. Setup permissions và menu

### Phase 2: Loyalty Module (Tuần 3-4)
1. Hệ thống tích điểm
2. Quản lý hạng thành viên
3. Vouchers
4. Missions & Badges
5. Vòng quay may mắn

### Phase 3: CRM Module (Tuần 5-6)
1. Customer Profiles 360°
2. RFM Calculator & Segmentation
3. Interactions tracking
4. Deals Pipeline
5. Automation rules
6. Email campaigns

### Phase 4: Affiliate Module (Tuần 7-8)
1. Partner management
2. Commission tracking
3. Payout system
4. Tracking & Analytics
5. Tier system

### Phase 5: Integration & Testing (Tuần 9-10)
1. Cross-module events
2. API endpoints
3. Performance optimization
4. Testing & QA

---

## Conventions & Best Practices

### Naming Conventions
- Tables: `{module}_` prefix (loyalty_*, crm_*, affiliate_*)
- Models: PascalCase without prefix (LoyaltyMember, not Loyalty_Member)
- Controllers: `{Resource}Controller.php`
- Services: `{Purpose}Service.php`

### Code Standards
- Logic nghiệp vụ đặt trong Services
- Controllers chỉ xử lý request/response
- Sử dụng Events/Listeners cho cross-module communication
- Không import models từ module khác trực tiếp

### Database
- Mọi bảng có business_id để multi-tenant
- Soft deletes cho dữ liệu quan trọng
- Indexes cho các trường tìm kiếm thường xuyên

---

*Tài liệu này sẽ được cập nhật trong quá trình triển khai.*

---

## 🚀 TIẾN ĐỘ THỰC TẾ (Cập nhật: 15/12/2024)

### ✅ Đã hoàn thành:

#### Database & Migrations
- [x] **Sepay**: Tất cả tables đã migrate (sepay_settings, sepay_transactions, sepay_payment_links)
- [x] **Loyalty**: Tất cả tables đã migrate (12 tables)
- [x] **Affiliate**: Tất cả tables đã migrate (7 tables)  
- [x] **CrmAdvanced**: Tất cả tables đã migrate (10 tables)

#### Entities/Models
- [x] **Sepay**: SepaySettings, SepayTransaction, SepayPaymentLink
- [x] **Loyalty**: LoyaltyTier, LoyaltyMember, PointTransaction, LoyaltySettings, LoyaltyVoucher, MemberVoucher, LoyaltyMission, MemberMission
- [x] **Affiliate**: AffiliateTier, AffiliatePartner, AffiliateCommission, AffiliateSettings
- [x] **CrmAdvanced**: CrmCustomerProfile, CrmRfmSettings, CrmPipeline, CrmPipelineStage, CrmDeal, CrmInteraction

#### Services
- [x] **Sepay**: SepayService (webhook processing, payment links, VietQR)
- [x] **Loyalty**: PointsService (earn, redeem, bonus points)
- [x] **Affiliate**: AffiliateService (click tracking, referral, commission)
- [x] **CrmAdvanced**: RfmCalculator (RFM scoring, segment assignment)

#### Controllers
- [x] **Sepay**: SepayController, WebhookController, InstallController, DataController
- [x] **Loyalty**: LoyaltyController (dashboard), DataController, InstallController
- [x] **Affiliate**: AffiliateController (dashboard), DataController, InstallController
- [x] **CrmAdvanced**: CrmAdvancedController (dashboard), DataController, InstallController

#### Routes
- [x] **Sepay**: Full admin routes + public webhook
- [x] **Loyalty**: Full admin routes + API routes
- [x] **Affiliate**: Full admin routes + public tracking
- [x] **CrmAdvanced**: Full admin routes

#### Views
- [x] **Sepay**: settings, transactions (with DataTables)
- [x] **Loyalty**: Dashboard view với stats
- [x] **Affiliate**: Dashboard view với stats
- [x] **CrmAdvanced**: Dashboard view với RFM segments

#### Event Integration
- [x] **TransactionCompleted Event**: Core event khi đơn hàng hoàn thành
- [x] **Loyalty Listener**: Tự động tích điểm
- [x] **Affiliate Listener**: Tự động tính hoa hồng
- [x] **CrmAdvanced Listener**: Tự động update RFM

#### Configuration
- [x] Tất cả modules đã có config.php với permissions và settings

### 🔄 Đang tiến hành:

1. **Views chi tiết**: 
   - Members management views
   - Voucher/Mission management views
   - Partner/Commission views
   - Customer 360° views
   - Pipeline/Deal Kanban views

2. **Controllers chi tiết**:
   - CRUD controllers cho từng entity
   - Settings controllers
   - Report controllers

3. **Additional Services**:
   - VoucherService (đổi voucher)
   - MissionService (tracking nhiệm vụ)
   - PayoutService (xử lý rút tiền)
   - AutomationEngine (tự động hóa CRM)

### ⏳ Chưa bắt đầu:

1. **Gamification**:
   - Wheel spin logic
   - Badge awarding
   - Leaderboards

2. **Email Marketing**:
   - Template builder
   - Campaign sending
   - Analytics

3. **Reports**:
   - Revenue reports
   - RFM analytics dashboard
   - Affiliate performance

4. **API Endpoints**:
   - Customer-facing APIs
   - Mobile app integration

### Module Status trong hệ thống:
```
[Enabled] Sepay
[Enabled] Loyalty  
[Enabled] Affiliate
[Enabled] CrmAdvanced
```

