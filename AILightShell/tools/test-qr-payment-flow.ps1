param(
    [string]$ApiBaseUrl = "http://192.168.132.109:8080",
    [string]$AccessDomain = "http://192.168.132.109:5173",
    [string]$UserPhone = "13800000000",
    [string]$UserName = "RN Tester",
    [string]$UserId = "rn_user_001",
    [int]$Qty = 1
)

$ErrorActionPreference = "Stop"

function Invoke-JsonApi {
    param(
        [string]$Method,
        [string]$Url,
        [object]$Body = $null,
        [hashtable]$Headers = @{}
    )

    $requestParams = @{
        Method      = $Method
        Uri         = $Url
        Headers     = $Headers
        ContentType = "application/json"
    }

    if ($null -ne $Body) {
        $requestParams.Body = ($Body | ConvertTo-Json -Depth 10)
    }

    return Invoke-RestMethod @requestParams
}

function Assert-ApiSuccess {
    param(
        [object]$Response,
        [string]$StepName
    )

    if ($Response.code -ne 0) {
        throw "$StepName failed: $($Response.message)"
    }
}

$traceId = "qr_flow_{0}" -f ([DateTimeOffset]::Now.ToUnixTimeMilliseconds())
$idempotentKey = "ps-order-$traceId"
$prepayKey = "ps-prepay-$traceId"
$notifyTxn = "txn_$traceId"

Write-Host "[1/6] Create order"
$createOrderBody = @{
    trace_id = $traceId
    user = @{
        user_id = $UserId
        name    = $UserName
        phone   = $UserPhone
    }
    address = @{
        full_address    = "Shanghai Pudong Test Rd 100"
        region          = "shanghai"
        province        = "Shanghai"
        city            = "Shanghai"
        district        = "Pudong"
        longitude       = 121.544
        latitude        = 31.221
        location_source = "SCRIPT"
        address_source  = "SCRIPT"
    }
    items = @(
        @{
            selected_old_sku = "OLD_001"
            selected_new_sku = "NEW-SKU-101"
            qty              = $Qty
        }
    )
    payable_total = 1990 * $Qty
    currency = "CNY"
    amount_unit = "FEN"
    access_domain = $AccessDomain
}
$createOrderResponse = Invoke-JsonApi -Method Post -Url "$ApiBaseUrl/create_order" -Body $createOrderBody -Headers @{
    "Idempotent-Key" = $idempotentKey
}
Assert-ApiSuccess -Response $createOrderResponse -StepName "create_order"
$orderId = $createOrderResponse.data.order_id
$payableTotal = $createOrderResponse.data.payable_total
$initialQr = $createOrderResponse.data.qr.qr_content
Write-Host "order_id=$orderId"
Write-Host "initial_qr=$initialQr"

Write-Host "[2/6] Refresh QR"
$refreshQrResponse = Invoke-JsonApi -Method Post -Url "$ApiBaseUrl/api/v1/orders/$orderId/qr" -Headers @{
    "X-User-Phone" = $UserPhone
}
Assert-ApiSuccess -Response $refreshQrResponse -StepName "generate_qr"
$qrContent = $refreshQrResponse.data.qr_content
$token = ([System.Uri]$qrContent).Query.TrimStart("?").Split("&") | Where-Object { $_ -like "token=*" } | ForEach-Object { $_.Substring(6) }
Write-Host "qr_content=$qrContent"

Write-Host "[3/6] Create prepay"
$prepayResponse = Invoke-JsonApi -Method Post -Url "$ApiBaseUrl/pay/prepay" -Body @{
    trace_id = $traceId
    order_id = $orderId
    amount = $payableTotal
    idempotent_key = $prepayKey
    openid = "openid_demo_script"
} -Headers @{
    "Idempotent-Key" = $prepayKey
}
Assert-ApiSuccess -Response $prepayResponse -StepName "pay_prepay"
$prepayId = $prepayResponse.data.prepay_id
Write-Host "prepay_id=$prepayId"

Write-Host "[4/6] Mock payment notify"
$notifyResponse = Invoke-JsonApi -Method Post -Url "$ApiBaseUrl/wechat/notify" -Body @{
    order_id = $orderId
    transaction_id = $notifyTxn
    status = "SUCCESS"
    paid_amount_fen = $payableTotal
    paid_at = [DateTimeOffset]::Now.ToString("o")
}
Assert-ApiSuccess -Response $notifyResponse -StepName "wechat_notify"
Write-Host "notify_status=$($notifyResponse.data.order_status)"

Write-Host "[5/6] Verify order result"
$getOrderResponse = Invoke-JsonApi -Method Get -Url "$ApiBaseUrl/get_order?order_id=$orderId"
Assert-ApiSuccess -Response $getOrderResponse -StepName "get_order"
if ($getOrderResponse.data.order_status -ne "PAID") {
    throw "Order verification failed: expected PAID, actual=$($getOrderResponse.data.order_status)"
}
Write-Host "order_status=$($getOrderResponse.data.order_status)"

Write-Host "[6/6] Verify public QR order page"
$publicViewResponse = Invoke-JsonApi -Method Get -Url "$ApiBaseUrl/order-view?order_id=$orderId&token=$token"
Assert-ApiSuccess -Response $publicViewResponse -StepName "order_view"
Write-Host "public_view_status=$($publicViewResponse.data.status)"

Write-Host ""
Write-Host "QR payment flow completed successfully."
Write-Host "order_id=$orderId"
Write-Host "qr_content=$qrContent"
Write-Host "transaction_id=$notifyTxn"
