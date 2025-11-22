from django import forms
from django.forms import ModelForm, Textarea
from django.utils.translation import gettext as _
from .models import (
Friend,
Message,
YaItemList,
YaItemDetail,
WowmaOrderInfo,
WowmaOrderDetail,
WowCategory,
)

class WowmaOrderinfoForm(ModelForm):
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['update_date'].widget.attrs['readonly'] = 'readonly'
    """

    class Meta:
        model = WowmaOrderInfo
        fields = ['orderid', 'site_and_device', 'mail_address', 'order_name', 'order_kana', 'order_zipcode',
                  'order_address', 'order_phone_number_1', 'order_phone_number_2', 'nickname', 'sender_name',
                  'sender_kana', 'sender_zipcode', 'sender_address', 'sender_phone_number_1', 'sender_phone_number_2',
                  'order_option', 'settlement_name', 'user_comment', 'memo', 'order_status', 'contact_status',
                  'authorization_status', 'payment_status', 'ship_status', 'print_status', 'cancel_status',
                  'cancel_reason', 'cancel_comment', 'total_sale_price', 'total_sale_unit', 'postage_price',
                  'charge_price', 'total_price', 'coupon_total_price', 'use_point', 'use_point_cancel',
                  'use_au_point_price', 'use_au_point', 'use_au_point_cancel', 'point_fixed_status', 'settle_status',
                  'pg_result', 'pg_orderid', 'pg_request_price', 'coupon_type', 'coupon_key', 'card_jagdement',
                  'delivery_name', 'delivery_method_id', 'delivery_request_time', 'shipping_carrier',
                  'shipping_number', 'create_date', 'order_date', 'contact_date',
                  #'shipping_number', 'create_date', 'update_date', 'order_date', 'contact_date',
                  'authorization_date', 'payment_date', 'ship_date', 'print_date', 'cancel_date',
                  'point_fixed_date', 'delivery_request_day', 'shipping_date',]
        widgets = {
            'site_and_device': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            'mail_address': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'order_name': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'order_kana': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'order_zipcode': forms.Textarea(attrs={'cols': 10, 'rows': 1}),
            'order_address': forms.Textarea(attrs={'cols': 80, 'rows': 3}),
            'order_phone_number_1': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            'order_phone_number_2': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            'nickname': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'sender_name': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'sender_kana': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'sender_zipcode': forms.Textarea(attrs={'cols': 10, 'rows': 1}),
            'sender_address': forms.Textarea(attrs={'cols': 80, 'rows': 3}),
            'sender_phone_number_1': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            'sender_phone_number_2': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            'order_option': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            'settlement_name': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            'user_comment': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'memo': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'order_status': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            'contact_status': forms.Textarea(attrs={'cols': 10, 'rows': 1}),
            'authorization_status': forms.Textarea(attrs={'cols': 10, 'rows': 1}),
            'payment_status': forms.Textarea(attrs={'cols': 10, 'rows': 1}),
            'ship_status': forms.Textarea(attrs={'cols': 10, 'rows': 1}),
            'print_status': forms.Textarea(attrs={'cols': 10, 'rows': 1}),
            'cancel_status': forms.Textarea(attrs={'cols': 10, 'rows': 1}),
            'cancel_reason': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            'cancel_comment': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            #'total_sale_price': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'total_sale_unit': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'postage_price': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'charge_price': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'total_price': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'coupon_total_price': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'use_point': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'use_point_cancel': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            #'use_au_point_price': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'use_au_point': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'use_au_point_cancel': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            'point_fixed_status': forms.Textarea(attrs={'cols': 10, 'rows': 1}),
            'settle_status': forms.Textarea(attrs={'cols': 10, 'rows': 1}),
            #'pg_result': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'pg_orderid': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'pg_request_price': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'coupon_type': forms.Textarea(attrs={'cols': 20, 'rows': 1}),
            'coupon_key': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            #'card_jagdement': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'delivery_name': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            'delivery_method_id': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            'delivery_request_time': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            #'shipping_carrier': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            'shipping_number': forms.Textarea(attrs={'cols': 30, 'rows': 1}),
            #'create_date': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'order_date': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'contact_date': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'authorization_date': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'payment_date': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'ship_date': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'print_date': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'cancel_date': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'point_fixed_date': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'delivery_request_day': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
            #'shipping_date': forms.Textarea(attrs={'cols': 50, 'rows': 1}),
        }


class KickYagetForm(forms.Form):
    YaUrl = forms.CharField(label='YaUrl', required=False)

class UpdByersCtListForm(forms.Form):
    YaUrl = forms.CharField(label='YaUrl', required=False)
    #file = forms.FileField()

class BuyersGoodsDetailImportForm(forms.Form):
    file = forms.FileField(label='BuyersGoodsDetailImportForm', required=True)

class BuyersGoodsDetailSmallImportForm(forms.Form):
    file = forms.FileField(label='BuyersGoodsDetailSmallImportForm', required=True)

class BuyersGoodsDeleteForm(forms.Form):
    file = forms.FileField(label='BuyersGoodsDeleteForm', required=True)

class YaItemListForm(forms.ModelForm):
    class Meta:
        model = YaItemList
        fields = ['bid', 'blink', 'gid', 'glink', 'g_img_src', 'g_img_alt']

class YaSetListToSheet(forms.Form):
    sheetnum = forms.CharField(label='sheetnum', required=False)

class HelloForm(forms.Form):
    name = forms.CharField(label='Name', empty_value=True)
    mail = forms.EmailField(label='Email', required=False)
    gender = forms.BooleanField(label='Gender',required=False)
    age = forms.IntegerField(label='Age')
    birthday = forms.DateField(label='Birth', required=False)

class FriendForm(forms.ModelForm):
    class Meta:
        model = Friend
        fields = ['name','mail','gender','age','birthday']

class FindForm(forms.Form):
    find = forms.CharField(label='Find', required=False)


class CheckForm(forms.Form):
    str = forms.CharField(label='String')

    def clean(self):
        cleaned_data = super().clean()
        str = cleaned_data['str']
        if (str.lower().startswith('no')):
            raise forms.ValidationError('You input "NO"!')

# from.models import Friend, Message

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['title','content','friend']

class YaBuyersItemDetailSearchForm(forms.Form):
    gid = forms.CharField(
        initial='',
        label='商品ID',
        required = False, # 必須ではない
    )
    glink = forms.CharField(
        initial='',
        label='商品リンク',
        required = False, # 必須ではない
    )
    gname = forms.CharField(
        initial='',
        label='商品名',
        required = False, # 必須ではない
    )
    gdetail = forms.CharField(
        initial='',
        label='商品詳細',
        required = False, # 必須ではない
    )
    gnormalprice = forms.CharField(
        initial='',
        label='通常価格',
        required = False, # 必須ではない
    )
    gspprice = forms.CharField(
        initial='',
        label='大量発注価格',
        required = False, # 必須ではない
    )
    gcode = forms.CharField(
        initial='',
        label='バイヤーズ商品コード',
        required = False, # 必須ではない
    )
    bu_ctid = forms.CharField(
        initial='',
        label='バイヤーズカテゴリコード',
        required = False, # 必須ではない
    )
    stock = forms.CharField(
        initial='',
        label='在庫数',
        required = False, # 必須ではない
    )
    wow_upd_status = forms.CharField(
        initial='',
        label='wowma掲載状況',
        required = False, # 必須ではない
    )
    wow_on_flg = forms.CharField(
        initial='',
        label='wowma出品ステータス',
        required = False, # 必須ではない
    )
    wow_lotnum = forms.CharField(
        initial='',
        label='wowmaロットナンバー',
        required = False, # 必須ではない
    )
    wow_gname = forms.CharField(
        initial='',
        label='wowma商品名',
        required = False, # 必須ではない
    )
    wow_gdetail = forms.CharField(
        initial='',
        label='wowma商品詳細',
        required = False, # 必須ではない
    )
    wow_worn_key = forms.CharField(
        initial='',
        label='wowma要注意キーワード',
        required = False, # 必須ではない
    )
    wow_price = forms.CharField(
        initial='',
        label='wowma価格',
        required = False, # 必須ではない
    )
    wow_fixed_price = forms.CharField(
        initial='',
        label='wowma固定価格',
        required = False, # 必須ではない
    )
    wow_postage_segment = forms.CharField(
        initial='',
        label='送料設定区分',
        required = False, # 必須ではない
    )
    wow_postage = forms.CharField(
        initial='',
        label='個別送料',
        required = False, # 必須ではない
    )
    wow_delivery_method_id = forms.CharField(
        initial='',
        label='配送方法ID',
        required = False, # 必須ではない
    )
    wow_ctid = forms.CharField(
        initial='',
        label='wowmaカテゴリID',
        required = False, # 必須ではない
    )
    qoo_upd_status = forms.CharField(
        initial='',
        label='qoo10掲載状況',
        required = False, # 必須ではない
    )
    qoo_on_flg = forms.CharField(
        initial='',
        label='qoo10ステータス',
        required = False, # 必須ではない
    )
    qoo_seller_code = forms.CharField(
        initial='',
        label='qoo販売者コード',
        required = False, # 必須ではない
    )
    qoo_gdno = forms.CharField(
        initial='',
        label='qoo商品コード',
        required = False, # 必須ではない
    )
    qoo_gname = forms.CharField(
        initial='',
        label='qoo10商品名',
        required = False, # 必須ではない
    )
    qoo_gdetail = forms.CharField(
        initial='',
        label='qoo10商品詳細',
        required = False, # 必須ではない
    )
    qoo_worn_key = forms.CharField(
        initial='',
        label='qoo10要注意キーワード',
        required = False, # 必須ではない
    )
    qoo_price = forms.CharField(
        initial='',
        label='qoo10価格',
        required = False, # 必須ではない
    )
    qoo_fixed_price = forms.CharField(
        initial='',
        label='qoo10固定価格',
        required = False, # 必須ではない
    )
    qoo_shipping_no = forms.CharField(
        initial='',
        label='qoo10送料コード',
        required = False, # 必須ではない
    )
    qoo_postage = forms.CharField(
        initial='',
        label='qoo10個別送料',
        required = False, # 必須ではない
    )
    qoo_delivery_method_id = forms.CharField(
        initial='',
        label='qoo10配送方法ID',
        required = False, # 必須ではない
    )
    qoo_ctid = forms.CharField(
        initial='',
        label='qoo10カテゴリID',
        required = False, # 必須ではない
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='作成日時from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='作成日時to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )

class BatchStatusSearchForm(forms.Form):
    batch_id = forms.CharField(
        initial='',
        label='バッチID',
        required = False, # 必須ではない
    )
    batch_name = forms.CharField(
        initial='',
        label='バッチ名',
        required = False, # 必須ではない
    )
    message = forms.CharField(
        initial='',
        label='メッセージ',
        required = False, # 必須ではない
    )
    batch_status = forms.fields.ChoiceField(
        label='状態',
        choices = (
            ('', '全件'),
            (0, '処理中'),
            (1, '完了'),
            (2, '異常終了'),
        ),
        required=False,  # 必須ではない
        widget=forms.widgets.Select
    )
    start_date_from = forms.DateTimeField(
        initial='',
        label='開始時刻from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    start_date_to = forms.DateTimeField(
        initial='',
        label='開始時刻to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    end_date_from = forms.DateTimeField(
        initial='',
        label='終了時刻from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    end_date_to = forms.DateTimeField(
        initial='',
        label='終了時刻to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    stop_date_from = forms.DateTimeField(
        initial='',
        label='中止時刻from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    stop_date_to = forms.DateTimeField(
        initial='',
        label='中止時刻to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='作成日時from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='作成日時to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )

class ErrorGoodsLogSearchForm(forms.Form):
    id = forms.CharField(
        initial='',
        label='バッチID',
        required = False, # 必須ではない
    )
    batch_name = forms.CharField(
        initial='',
        label='バッチ名',
        required = False, # 必須ではない
    )
    gid = forms.CharField(
        initial='',
        label='商品ID',
        required = False, # 必須ではない
    )
    status = forms.CharField(
        initial='',
        label='状態',
        required = False, # 必須ではない
    )
    code = forms.CharField(
        initial='',
        label='code',
        required = False, # 必須ではない
    )
    message = forms.CharField(
        initial='',
        label='メッセージ',
        required = False, # 必須ではない
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='作成日時from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='作成日時to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )

class AllOrderInfoForm(forms.Form):
    qoo_id = forms.CharField(
        initial='',
        label='qoo_id',
        required = False, # 必須ではない
    )
    wow_id = forms.CharField(
        initial='',
        label='wow_id',
        required = False, # 必須ではない
    )
    buyer = forms.CharField(
        initial='',
        label='buyer',
        required = False, # 必須ではない
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='作成日時from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='作成日時to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )

class QooOrderInfoForm(forms.Form):
    seller_id = forms.CharField(
        initial='',
        label='販売者ID',
        required = False, # 必須ではない
    )
    order_no = forms.CharField(
        initial='',
        label='order_no',
        required = False, # 必須ではない
    )
    shipping_status = forms.CharField(
        initial='',
        label='配送状態',
        required = False, # 必須ではない
    )
    buyer = forms.CharField(
        initial='',
        label='注文者氏名',
        required = False, # 必須ではない
    )
    order_date = forms.CharField(
        initial='',
        label='注文日',
        required = False, # 必須ではない
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='作成日時from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='作成日時to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )

class QooShopInfoForm(forms.Form):
    my_shop_num = forms.CharField(
        initial='',
        label='ショップ番号',
        required = False, # 必須ではない
    )
    shop_name = forms.CharField(
        initial='',
        label='ショップ名',
        required = False, # 必須ではない
    )
    user_id = forms.CharField(
        initial='',
        label='ユーザID',
        required = False, # 必須ではない
    )
    shop_status = forms.CharField(
        initial='0',
        label='ステータス',
        required = False, # 必須ではない
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='作成日時from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='作成日時to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )

class WowOrderInfoForm(forms.Form):
    orderid = forms.CharField(
        initial='',
        label='注文ID',
        required = False, # 必須ではない
    )
    shop_id = forms.CharField(
        initial='',
        label='ショップID',
        required = False, # 必須ではない
    )
    order_status = forms.CharField(
        initial='',
        label='注文状態',
        required = False, # 必須ではない
    )
    ship_status = forms.CharField(
        initial='',
        label='配送状態',
        required = False, # 必須ではない
    )
    order_name = forms.CharField(
        initial='',
        label='注文者氏名',
        required = False, # 必須ではない
    )
    user_comment = forms.CharField(
        initial='',
        label='ユーザコメント',
        required = False, # 必須ではない
    )
    order_date = forms.DateTimeField(
        initial='',
        label='注文日',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='作成日時from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='作成日時to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )

class WowShopInfoForm(forms.Form):
    my_shop_num = forms.CharField(
        initial='',
        label='ショップ番号',
        required = False, # 必須ではない
    )
    shop_name = forms.CharField(
        initial='',
        label='ショップ名',
        required = False, # 必須ではない
    )
    shop_id = forms.CharField(
        initial='',
        label='ショップID',
        required = False, # 必須ではない
    )
    shop_status = forms.CharField(
        initial='0',
        label='ステータス',
        required = False, # 必須ではない
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='作成日時from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='作成日時to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )

class BlackListForm(forms.Form):
    gid = forms.CharField(
        initial='',
        label='商品ID',
        required = False, # 必須ではない
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='作成日時from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='作成日時to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )


class YaImpSpapiUpdCsvForm(forms.Form):
    file = forms.FileField(label='YaImpSpapiUpdCsv', required=True)


class QooAsinUpdCsvForm(forms.Form):
    file = forms.FileField(label='QooAsinUpdCsv', required=True)


class QooAsinUpdCsvFormBk(forms.Form):
    file = forms.FileField(label='QooAsinUpdCsv', required=True)


class QooAsinUpdAsinForm(forms.Form):
    asin = forms.CharField(
        initial='',
        label='asin（必須）',
        required=True,  # 必須
    )
    """
    wholesale_price = forms.CharField(
        initial='卸価格を入力',
        label='wholesale_price',
        required=False,  # 必須ではない
    )
    wholesale_name = forms.CharField(
        initial='卸業者名を入力',
        label='wholesale_name',
        required=False,  # 必須ではない
    )
    """


class AmaCategoryForm(forms.Form):
    product_cat_id = forms.IntegerField(
        initial=0,
        label='product_cat_id',
        required=False,  # 必須ではない
    )
    product_cat_name = forms.CharField(
        initial='',
        label='product_cat_name',
        required=False,  # 必須ではない
    )
    parent_cat_id = forms.IntegerField(
        initial=0,
        label='parent_cat_id',
        required=False,  # 必須ではない
    )
    level_1_cat_id = forms.CharField(
        initial=0,
        label='level_1_cat_id',
        required=False,  # 必須ではない
    )
    level_2_cat_id = forms.CharField(
        initial=0,
        label='level_2_cat_id',
        required=False,  # 必須ではない
    )
    level_3_cat_id = forms.CharField(
        initial=0,
        label='level_3_cat_id',
        required=False,  # 必須ではない
    )
    level_4_cat_id = forms.CharField(
        initial=0,
        label='level_4_cat_id',
        required=False,  # 必須ではない
    )
    level_5_cat_id = forms.CharField(
        initial=0,
        label='level_5_cat_id',
        required=False,  # 必須ではない
    )
    level_6_cat_id = forms.CharField(
        initial=0,
        label='level_6_cat_id',
        required=False,  # 必須ではない
    )
    level_7_cat_id = forms.CharField(
        initial=0,
        label='level_7_cat_id',
        required=False,  # 必須ではない
    )
    level_8_cat_id = forms.CharField(
        initial=0,
        label='level_8_cat_id',
        required=False,  # 必須ではない
    )
    level_1_cat_name = forms.CharField(
        initial='',
        label='level_1_cat_name',
        required=False,  # 必須ではない
    )
    level_2_cat_name = forms.CharField(
        initial='',
        label='level_2_cat_name',
        required=False,  # 必須ではない
    )
    level_3_cat_name = forms.CharField(
        initial='',
        label='level_3_cat_name',
        required=False,  # 必須ではない
    )
    level_4_cat_name = forms.CharField(
        initial='',
        label='level_4_cat_name',
        required=False,  # 必須ではない
    )
    level_5_cat_name = forms.CharField(
        initial='',
        label='level_5_cat_name',
        required=False,  # 必須ではない
    )
    level_6_cat_name = forms.CharField(
        initial='',
        label='level_6_cat_name',
        required=False,  # 必須ではない
    )
    level_7_cat_name = forms.CharField(
        initial='',
        label='level_7_cat_name',
        required=False,  # 必須ではない
    )
    level_8_cat_name = forms.CharField(
        initial='',
        label='level_8_cat_name',
        required=False,  # 必須ではない
    )
    qoo_cat_id = forms.CharField(
        initial='',
        label='qoo_cat_id',
        required=False,  # 必須ではない
    )
    wow_cat_id = forms.CharField(
        initial='',
        label='wow_cat_id',
        required=False,  # 必須ではない
    )
    yahoo_cat_id = forms.CharField(
        initial='',
        label='yahoo_cat_id',
        required=False,  # 必須ではない
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='create_date_from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='create_date_to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )


class WowCategoryForm(forms.Form):
    product_cat_id = forms.IntegerField(
        initial=0,
        label='product_cat_id',
        required=False,  # 必須ではない
    )
    product_cat_name = forms.CharField(
        initial='',
        label='product_cat_name',
        required=False,  # 必須ではない
    )
    level_1_cat_name = forms.CharField(
        initial='',
        label='level_1_cat_name',
        required=False,  # 必須ではない
    )
    level_2_cat_name = forms.CharField(
        initial='',
        label='level_2_cat_name',
        required=False,  # 必須ではない
    )
    level_3_cat_name = forms.CharField(
        initial='',
        label='level_3_cat_name',
        required=False,  # 必須ではない
    )
    level_4_cat_name = forms.CharField(
        initial='',
        label='level_4_cat_name',
        required=False,  # 必須ではない
    )
    ama_level_1_cat_id = forms.CharField(
        initial='',
        label='ama_level_1_cat_id',
        required=False,  # 必須ではない
    )
    ama_level_2_cat_id = forms.CharField(
        initial='',
        label='ama_level_2_cat_id',
        required=False,  # 必須ではない
    )
    ama_level_3_cat_id = forms.CharField(
        initial='',
        label='ama_level_3_cat_id',
        required=False,  # 必須ではない
    )
    ama_level_1_cat_name = forms.CharField(
        initial='',
        label='ama_level_1_cat_name',
        required=False,  # 必須ではない
    )
    ama_level_2_cat_name = forms.CharField(
        initial='',
        label='ama_level_2_cat_name',
        required=False,  # 必須ではない
    )
    ama_level_3_cat_name = forms.CharField(
        initial='',
        label='ama_level_3_cat_name',
        required=False,  # 必須ではない
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='create_date_from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='create_date_to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )


class WowCategoryModelForm(forms.ModelForm):
    product_cat_id = forms.IntegerField(
        initial=0,
        label='product_cat_id',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False,  # 必須ではない
        error_messages={
            'unique': _('既に同じカテゴリIDが存在します'),
        },
    )
    product_cat_name = forms.CharField(
        initial='',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='product_cat_name',
        required=False,  # 必須ではない
    )
    level_1_cat_name = forms.CharField(
        initial='',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='level_1_cat_name',
        required=False,  # 必須ではない
    )
    level_2_cat_name = forms.CharField(
        initial='',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='level_2_cat_name',
        required=False,  # 必須ではない
    )
    level_3_cat_name = forms.CharField(
        initial='',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='level_3_cat_name',
        required=False,  # 必須ではない
    )
    level_4_cat_name = forms.CharField(
        initial='',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='level_4_cat_name',
        required=False,  # 必須ではない
    )
    ama_level_1_cat_id = forms.CharField(
        initial='',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='ama_level_1_cat_id',
        required=False,  # 必須ではない
    )
    ama_level_2_cat_id = forms.CharField(
        initial='',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='ama_level_2_cat_id',
        required=False,  # 必須ではない
    )
    ama_level_3_cat_id = forms.CharField(
        initial='',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='ama_level_3_cat_id',
        required=False,  # 必須ではない
    )
    ama_level_1_cat_name = forms.CharField(
        initial='',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='ama_level_1_cat_name',
        required=False,  # 必須ではない
    )
    ama_level_2_cat_name = forms.CharField(
        initial='',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='ama_level_2_cat_name',
        required=False,  # 必須ではない
    )
    ama_level_3_cat_name = forms.CharField(
        initial='',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='ama_level_3_cat_name',
        required=False,  # 必須ではない
    )
    create_date = forms.DateTimeField(
        initial='',
        widget=forms.DateInput(attrs={"type": "date"}),
        label='create_date',
        required=False,  # 必須ではない
        input_formats=['%Y-%m-%d']
    )

    class Meta:
        """ フォームのメタ情報 """
        model = WowCategory
        fields = [
            'product_cat_id', 'product_cat_name', 'level_1_cat_name',
            'level_2_cat_name', 'level_3_cat_name', 'level_4_cat_name',
            'ama_level_1_cat_id', 'ama_level_2_cat_id', 'ama_level_3_cat_id',
            'ama_level_1_cat_name', 'ama_level_2_cat_name', 'ama_level_3_cat_name',
            'create_date',
        ]


class AmaWowSelectForm(forms.Form):
    five = forms.MultipleChoiceField(
        label='AmaWowSelectFormです',
        required=False,
        disabled=False,
        widget=forms.RadioSelect(attrs={
            'id': 'five', 'class': 'form-check-input'}))


class QooAsinDetailSearchForm(forms.Form):
    csv_no = forms.CharField(
        initial='',
        label='csv_no',
        required=False,  # 必須ではない
    )
    asin = forms.CharField(
        initial='',
        label='asin',
        required=False,  # 必須ではない
    )
    shopid = forms.CharField(
        initial='',
        label='shopid',
        required=False,  # 必須ではない
    )
    y_cat_1 = forms.CharField(
        initial='',
        label='y_cat_1',
        required=False,  # 必須ではない
    )
    myshop_cat_1 = forms.CharField(
        initial='',
        label='myshop_cat_1',
        required=False,  # 必須ではない
    )
    myshop_cat_2 = forms.CharField(
        initial='',
        label='myshop_cat_2',
        required=False,  # 必須ではない
    )
    is_blacklist_ok_img = forms.BooleanField(
        label='is_blacklist_ok_img',
        required=False,  # 必須ではない
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='create_date_from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='create_date_to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )


class WowGoodsListSearchForm(forms.Form):
    id = forms.CharField(
        initial='',
        label='ID',
        required = False, # 必須ではない
    )
    gid = forms.CharField(
        initial='',
        label='gid',
        required=False,  # 必須ではない
    )
    gcode = forms.CharField(
        initial='',
        label='gcode',
        required=False,  # 必須ではない
    )
    asin = forms.CharField(
        initial='',
        label='asin',
        required=False,  # 必須ではない
    )
    wow_lotnum = forms.IntegerField(
        label='wow_lotnum',
        required=False,  # 必須ではない
    )
    wow_upd_status = forms.IntegerField(
        label='wow_upd_status',
        required=False,  # 必須ではない
    )
    wow_on_flg = forms.IntegerField(
        label='wow_on_flg',
        required=False,  # 必須ではない
    )
    wow_ng_flg = forms.BooleanField(
        label='wow_ng_flg',
        required=False,  # 必須ではない
    )
    wow_gname = forms.CharField(
        initial='',
        label='wow_gname',
        required=False,  # 必須ではない
    )
    wow_gdetail = forms.CharField(
        initial='',
        label='wow_gdetail',
        required=False,  # 必須ではない
    )
    wow_keyword = forms.CharField(
        initial='',
        label='wow_keyword',
        required=False,  # 必須ではない
    )
    wow_worn_key = forms.CharField(
        initial='',
        label='wow_worn_key',
        required=False,  # 必須ではない
    )
    wow_price = forms.IntegerField(
        label='wow_price',
        required=False,  # 必須ではない
    )
    wow_fixed_price = forms.IntegerField(
        label='wow_fixed_price',
        required=False,  # 必須ではない
    )
    wow_postage_segment = forms.IntegerField(
        label='wow_postage_segment',
        required=False,  # 必須ではない
    )
    wow_postage = forms.IntegerField(
        label='wow_postage',
        required=False,  # 必須ではない
    )
    wow_delivery_method_id = forms.IntegerField(
        label='wow_delivery_method_id',
        required=False,  # 必須ではない
    )
    ama_ctid = forms.IntegerField(
        initial='',
        label='ama_ctid',
        required=False,  # 必須ではない
    )
    wow_ctid = forms.IntegerField(
        initial='',
        label='wow_ctid',
        required=False,  # 必須ではない
    )
    wow_tagid = forms.CharField(
        initial='',
        label='wow_tagid',
        required=False,  # 必須ではない
    )
    create_date_from = forms.DateTimeField(
        initial='',
        label='create_date_from',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
    create_date_to = forms.DateTimeField(
        initial='',
        label='create_date_to',
        required=False,  # 必須ではない
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=['%Y-%m-%d']
    )
