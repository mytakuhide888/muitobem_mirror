import re
from datetime import datetime
from django.utils.timezone import now
from django.utils import timezone
from django.db import models
from django.core.validators import ValidationError


def alpha_only(value):
    if (re.match(r'^[a-zA-Z]*$', value) == None):
        raise ValidationError(
            'Enter only alphabet!', \
            params={'value': value},
        )

class YaListUrl(models.Model):
    targeturl = models.TextField(max_length=500, default='')
    filename = models.TextField(max_length=30, default='')
    create_date = models.DateTimeField(default=timezone.now)

    update_date = models.DateTimeField(null=True, blank=True)
    db_update_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return '<YaListUrl:id=' + str(self.id) + ', ' + \
               'filename[' + self.filename + '] >'

class YaShopListUrl(models.Model):
    targeturl = models.TextField(max_length=500, default='')
    filename = models.TextField(max_length=30, default='')
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True)
    db_update_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return '<YaShopListUrl:id=' + str(self.id) + ', ' + \
               'filename[' + self.filename + '] >'


class YaItemList(models.Model):
    bid = models.CharField(max_length=50, default='')
    blink = models.TextField(max_length=300, default='')
    gid = models.CharField(max_length=50, default='', primary_key=True)
    glink = models.TextField(max_length=300, default='')
    g_img_src = models.TextField(max_length=300, default='')
    g_img_alt = models.TextField(max_length=300, default='')
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return '<YaItemList:id=' + str(self.id) + ', ' + \
               'bid[' + self.bid + '] gid[' + self.gid + '] >'

    class Meta:
        unique_together = (("bid", "gid"))


class YaShopItemList(models.Model):
    shopid = models.CharField(max_length=50, default='')
    shoplink = models.TextField(max_length=300, default='')
    gid = models.CharField(max_length=50, default='', primary_key=True)
    glink = models.TextField(max_length=300, default='')
    g_img_src = models.TextField(max_length=300, default='')
    g_img_alt = models.TextField(max_length=300, default='')
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return '<YaShopItemList:id=' + str(self.id) + ', ' + \
               'shopid[' + self.shopid + '] gid[' + self.gid + '] >'

    class Meta:
        unique_together = (("shopid", "gid"))


class YaItemDetail(models.Model):
    bid = models.TextField(max_length=50, default='')
    blink = models.TextField(max_length=300, default='')
    gid = models.TextField(max_length=50, default='')
    glink = models.TextField(max_length=300, default='')
    gtitle = models.TextField(max_length=300, default='')
    g_n_val = models.TextField(max_length=300, default='')
    g_s_val = models.TextField(max_length=300, default='')
    g_detail = models.TextField(max_length=300, default='')
    g_img_srcs = models.JSONField(
        null=True, blank=True, default=list,
        help_text="商品画像URLの配列（旧: g_img_src_1..20）"
    )

    g_img_alts = models.JSONField(
        null=True, blank=True, default=list,
        help_text="商品画像ALTテキストの配列（旧: g_img_alt_1..20）"
    )

    g_det_titles = models.JSONField(
        null=True, blank=True, default=list,
        help_text="詳細セクションの見出し配列（旧: g_det_title_1..15）"
    )

    g_det_conts = models.JSONField(
        null=True, blank=True, default=list,
        help_text="詳細セクション本文の配列（旧: g_det_cont_1..15）"
    )

    create_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return '<YaItemDetail:id=' + str(self.id) + ', ' + \
               'bid[' + self.bid + '] gid[' + self.gid + '] >'


class YaAmaGoodsDetail(models.Model):
    asin = models.TextField(max_length=12, default='')
    title = models.TextField(max_length=300, default='')
    url = models.URLField()
    amount = models.FloatField()
    binding = models.TextField(max_length=200, default='')
    brand = models.TextField(max_length=100, default='')
    color = models.TextField(max_length=500, default='')
    department = models.TextField(max_length=200, default='')
    is_adlt = models.BooleanField()
    i_height = models.FloatField()
    i_length = models.FloatField()
    i_width = models.FloatField()
    i_weight = models.FloatField()
    p_height = models.FloatField()
    p_length = models.FloatField()
    p_width = models.FloatField()
    p_weight = models.FloatField()
    rank_cat_1 = models.TextField(max_length=100, default='')
    rank_1 = models.IntegerField()
    rank_cat_2 = models.TextField(max_length=100, default='')
    rank_2 = models.IntegerField()
    rank_cat_3 = models.TextField(max_length=100, default='')
    rank_3 = models.IntegerField()
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True)
    bid = models.TextField(max_length=50, default='')
    gid = models.TextField(max_length=50, default='')
    #gid = models.ForeignKey(YaItemList, to_field = 'gid', on_delete=models.CASCADE)

    def __str__(self):
        return '<YaAmaGoodsDetail:asin=' + str(self.asin) + ', ' + \
               'title[' + self.title + '] >'


class YaShopAmaGoodsDetail(models.Model):
    asin = models.TextField(max_length=12, default='')
    title = models.TextField(max_length=300, default='')
    url = models.URLField()
    amount = models.FloatField()
    binding = models.TextField(max_length=200, default='')
    brand = models.TextField(max_length=100, default='')
    color = models.TextField(max_length=500, default='')
    department = models.TextField(max_length=200, default='')
    is_adlt = models.BooleanField()
    i_height = models.FloatField()
    i_length = models.FloatField()
    i_width = models.FloatField()
    i_weight = models.FloatField()
    p_height = models.FloatField()
    p_length = models.FloatField()
    p_width = models.FloatField()
    p_weight = models.FloatField()
    rank_cat_1 = models.TextField(max_length=100, default='')
    rank_1 = models.IntegerField()
    rank_cat_2 = models.TextField(max_length=100, default='')
    rank_2 = models.IntegerField()
    rank_cat_3 = models.TextField(max_length=100, default='')
    rank_3 = models.IntegerField()
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True)
    shopid = models.TextField(max_length=50, default='')
    gid = models.TextField(max_length=50, default='')
    #gid = models.ForeignKey(YaItemList, to_field = 'gid', on_delete=models.CASCADE)

    def __str__(self):
        return '<YaShopAmaGoodsDetail:asin=' + str(self.asin) + ', ' + \
               'title[' + self.title + '] >'


# バイヤーズのリストページに掲載されている商品情報。商品詳細はここから深堀りする
class YaBuyersItemList(models.Model):
    gid = models.CharField('商品ID', max_length=30, primary_key=True) # B111 + バイヤーズの商品ID  B111000000023078 など
    gcd = models.TextField('バイヤーズ商品コード', max_length=30, default='',null=True, blank=True)
    my_ct = models.TextField('バイヤーズカテゴリコード', max_length=30, default='', null=True, blank=True)
    listurl = models.TextField('リストページURl', max_length=300, default='',null=True, blank=True)
    glink = models.TextField('商品リンク', max_length=300, default='',null=True, blank=True)
    gname = models.TextField('商品名', max_length=300, default='',null=True, blank=True)
    g_img_src = models.TextField('イメージ画像URL', max_length=300, default='',null=True, blank=True)
    create_date = models.DateTimeField('作成時間', default=timezone.now)
    update_date = models.DateTimeField('更新時間', null=True, blank=True)

    def __str__(self):
        return '<YaBuyersItemList:id=' + str(self.id) + ', ' + \
               'gid[' + self.gid + '] glink[' + self.glink + '] >'

    class Meta:
        verbose_name = 'バイヤーズ商品リスト'
        verbose_name_plural = 'バイヤーズ商品リスト'


class YaBuyersItemBlackList(models.Model):
    gid = models.CharField('商品ID', max_length=30, primary_key=True)  # B111 + バイヤーズの商品ID  B111000000023078 など
    create_date = models.DateTimeField('作成時間', default=timezone.now)
    update_date = models.DateTimeField(
        '更新時間', auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<YaBuyersItemBlackList:gid=' + str(self.gid) + '>'

    class Meta:
        verbose_name = 'バイヤーズ商品ブラックリスト'
        verbose_name_plural = 'バイヤーズ商品ブラックリスト'


class YaBuyersItemDetail(models.Model):
    gid = models.CharField('商品ID', max_length=30, primary_key=True)  # B111 + バイヤーズの商品ID  B111000000023078 など
    glink = models.TextField('商品リンク', max_length=300, default='', null=True, blank=True)
    ss_url = models.TextField('リンク元リストページURL', max_length=300, default='', null=True, blank=True)
    bu_ctid = models.TextField('バイヤーズカテゴリID', max_length=100, default='', null=True, blank=True)  # バイヤーズカテゴリID
    gsrc = models.TextField('サムネイル画像URL', max_length=300, default='', null=True, blank=True)
    gname = models.TextField('商品名', max_length=300, default='', null=True, blank=True)  # バイヤーズの商品名
    gdetail = models.TextField('商品詳細', max_length=2000, default='', null=True, blank=True)  # バイヤーズの商品詳細
    gnormalprice = models.IntegerField('通常価格', default=0, null=True, blank=True)  # バイヤーズ上の通常価格
    gspprice = models.IntegerField('大量発注価格', default=0, null=True, blank=True)
    gcode = models.TextField('バイヤーズ商品コード', max_length=30, default='', null=True, blank=True) # バイヤーズの商品コード btab089 など
    stock = models.IntegerField('在庫数', default=0, null=True, blank=True)  # バイヤーズ上の在庫数
    WOW_UPD_STATUS = ((0, '未登録'), (1, '掲載中'), (2, '登録済みだが未掲載'))
    wow_upd_status = models.IntegerField('wow掲載状況', choices=WOW_UPD_STATUS, default=0, null=True, blank=True) # wowmaの掲載ステータス
    WOW_STATUS = ((0, '確認待ち'), (1, 'OK'), (2, 'NG'), (3, '在庫切れ'))
    wow_on_flg = models.IntegerField('wowステータス', choices=WOW_STATUS, default=0, null=True, blank=True)  # wowmaの出品ステータス　NG はブラックリスト
    wow_gname = models.TextField('wowma商品名', max_length=300, default='', null=True, blank=True)  # wowmaの商品名
    wow_gdetail = models.TextField('wowma商品詳細', max_length=2000, default='', null=True, blank=True) # wowmaの商品詳細
    wow_lotnum = models.IntegerField('wowmaロットナンバー', default=0, null=True, blank=True)  # wowmaロットナンバー
    wow_keyword = models.TextField('wowma検索キーワード', max_length=350, default='', null=True, blank=True) # wowmaの検索ワード 20文字 x 3個まで設定可能(ex: シャツ、デニムシャツ、デニムのシャツ)Max 10 keywords, a keyword: Max 30　
    wow_worn_key = models.TextField('wowma要注意キーワード', max_length=200, default='', null=True, blank=True) # wowmaの商品詳細に含まれる危険ワード
    wow_price = models.IntegerField('wowma価格', default=0, null=True, blank=True) # wowmaの価格
    wow_fixed_price = models.IntegerField('wowma固定価格', default=0, null=True, blank=True) # wowmaの固定価格。もしこれが0より大きければ優先される
    wow_postage_segment = models.IntegerField('送料設定区分', default=2, null=True, blank=True)  # wowmaの# 送料設定区分 1:送料別/2:送料込み/3:個別送料
    wow_postage = models.IntegerField('個別送料', default=0, null=True, blank=True)  # wowmaの個別送料
    wow_delivery_method_id = models.IntegerField('配送方法ID', default=0, null=True, blank=True)  # wowmaの配送方法ID
    wow_ctid = models.IntegerField('カテゴリID', default=0, null=True, blank=True)  # wowmaのカテゴリID
    wow_tagid = models.TextField('タグID', default='', null=True, blank=True)  # wowmaの検索タグID　20文字 x 64個まで指定可能 半角スペース区切りで保持する
    QOO_UPD_STATUS = ((1, '取引待機'), (2, '取引可能'), (3, '取引廃止'))
    qoo_upd_status = models.IntegerField('qoo掲載状況', choices=QOO_UPD_STATUS, default=1, null=True, blank=True) # qooの掲載ステータス 取引待機= 1、取引可能= 2、取引廃止= 3）
    qoo_seller_code = models.TextField('qoo販売者コード', max_length=100, default='', null=True, blank=True) # qooの販売者独自のコード
    qoo_gdno = models.TextField('qoo商品コード', max_length=100, default='', null=True, blank=True) # 登録された商品のQoo10商品コード
    QOO_STATUS = ((0, '確認待ち'), (1, 'OK'), (2, 'NG'), (3, '在庫切れ'))
    qoo_on_flg = models.IntegerField('qooステータス', choices=QOO_STATUS, default=0, null=True, blank=True) # qooの出品ステータス　NG はブラックリスト
    qoo_gname = models.TextField('qoo商品名', max_length=300, default='', null=True, blank=True) # qooの商品名
    qoo_promotion_name = models.TextField('qoo広告文', max_length=20, default='', null=True, blank=True) # qooの広告文
    qoo_model_name = models.TextField('qooモデル名', max_length=30, default='', null=True, blank=True) # qooのモデル名
    qoo_gdetail = models.TextField('qoo商品詳細', max_length=2000, default='', null=True, blank=True) # qooの商品詳細
    qoo_keyword = models.TextField('qoo検索キーワード', max_length=350, default='', null=True, blank=True) # qooの検索ワード 10個まで設定可能(ex: シャツ、デニムシャツ、デニムのシャツ)Max 10 keywords, a keyword: Max 30　
    qoo_worn_key = models.TextField('qoo要注意キーワード', max_length=200, default='', null=True, blank=True) # qooの商品詳細に含まれる危険ワード
    qoo_contact_info = models.TextField('qooアフターサービス情報', max_length=100, default='', null=True, blank=True) # qooのアフターサービス情報
    qoo_price = models.IntegerField('qoo価格', default=0, null=True, blank=True) # qooの価格
    qoo_postage_segment = models.IntegerField('送料設定区分', default=2, null=True, blank=True)  # qooの# 送料設定区分 1:送料別/2:送料込み/3:個別送料
    qoo_fixed_price = models.IntegerField('qoo固定価格', default=0, null=True, blank=True) # qooの固定価格。もしこれが0より大きければ優先される
    qoo_shipping_no = models.IntegerField('qoo送料コード', default=0, null=True, blank=True)  # qooの送料コード 0:送料無料
    qoo_available_date_type = models.TextField('qoo商品発送可能日タイプ', max_length=1, default='0', null=True, blank=True) # 商品発送可能日タイプ
    qoo_available_date_value = models.TextField('qoo商品発送可能日タイプの詳細', max_length=10, default='0', null=True, blank=True) # 商品発送可能日タイプの詳細
    qoo_postage = models.IntegerField('qoo個別送料', default=0, null=True, blank=True)  # qooの個別送料
    qoo_delivery_method_id = models.IntegerField('qoo配送方法ID', default=0, null=True, blank=True)  # qooの配送方法ID
    qoo_item_qty = models.IntegerField('qoo商品数量', default=1, null=True, blank=True)  # qooの商品数量
    qoo_ctid = models.IntegerField('qoo10カテゴリID', default=0, null=True, blank=True)  # qooのカテゴリID
    qoo_standard_img = models.TextField('qoo商品代表画像URL', max_length=200, default='', null=True, blank=True)
    qoo_video_url = models.TextField('qoo商品動画URL', max_length=200, default='', null=True, blank=True)
    qoo_additional_opt = models.TextField('qoo追加オプション項目', max_length=500, default='', null=True, blank=True)
    qoo_item_type = models.TextField('qoo商品タイプ', max_length=500, default='', null=True, blank=True)
    qoo_expire_date = models.DateTimeField('qoo商品の販売終了日', default=None, null=True, blank=True)
    QOO_ADULT_YN = (('Y', 'アダルト商品'), ('N', 'アダルト商品ではない'))
    qoo_adult_yn = models.TextField('qooアダルトフラグ', choices=QOO_ADULT_YN, default='N', null=True, blank=True) # qooのアダルトフラグ
    g_img_src_1 = models.TextField('画像URL_1', max_length=300, default='', null=True, blank=True)
    g_img_src_2 = models.TextField('画像URL_2', max_length=300, default='', null=True, blank=True)
    g_img_src_3 = models.TextField('画像URL_3', max_length=300, default='', null=True, blank=True)
    g_img_src_4 = models.TextField('画像URL_4', max_length=300, default='', null=True, blank=True)
    g_img_src_5 = models.TextField('画像URL_5', max_length=300, default='', null=True, blank=True)
    g_img_src_6 = models.TextField('画像URL_6', max_length=300, default='', null=True, blank=True)
    g_img_src_7 = models.TextField('画像URL_7', max_length=300, default='', null=True, blank=True)
    g_img_src_8 = models.TextField('画像URL_8', max_length=300, default='', null=True, blank=True)
    g_img_src_9 = models.TextField('画像URL_9', max_length=300, default='', null=True, blank=True)
    g_img_src_10 = models.TextField('画像URL_10', max_length=300, default='', null=True, blank=True)
    g_img_src_11 = models.TextField('画像URL_11', max_length=300, default='', null=True, blank=True)
    g_img_src_12 = models.TextField('画像URL_12', max_length=300, default='', null=True, blank=True)
    g_img_src_13 = models.TextField('画像URL_13', max_length=300, default='', null=True, blank=True)
    g_img_src_14 = models.TextField('画像URL_14', max_length=300, default='', null=True, blank=True)
    g_img_src_15 = models.TextField('画像URL_15', max_length=300, default='', null=True, blank=True)
    g_img_src_16 = models.TextField('画像URL_16', max_length=300, default='', null=True, blank=True)
    g_img_src_17 = models.TextField('画像URL_17', max_length=300, default='', null=True, blank=True)
    g_img_src_18 = models.TextField('画像URL_18', max_length=300, default='', null=True, blank=True)
    g_img_src_19 = models.TextField('画像URL_19', max_length=300, default='', null=True, blank=True)
    g_img_src_20 = models.TextField('画像URL_20', max_length=300, default='', null=True, blank=True)
    black_list = models.ForeignKey(YaBuyersItemBlackList, verbose_name='ブラックリスト', null=True, on_delete=models.DO_NOTHING)
    create_date = models.DateTimeField('作成時間', default=timezone.now)
    update_date = models.DateTimeField('更新時間', auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<YaBuyersItemDetail:gid=' + str(self.gid) + ', ' + \
               'gname[' + self.gname + '] >'

    class Meta:
        verbose_name = 'バイヤーズ商品詳細'
        verbose_name_plural = 'バイヤーズ商品詳細'


# 商品詳細のショップID毎に必要な情報（親はYaBuyersItemDetail)
class YaBuyersItemDetailEachShopInfo(models.Model):
    detail = models.ForeignKey(YaBuyersItemDetail, on_delete=models.CASCADE)
    wow_shop_num = models.IntegerField('Wowmaショップ番号', default=0, null=True, blank=True)  # wowma　ショップの通し番号 my_shop_num
    qoo_shop_num = models.IntegerField('Qoo10ショップ番号', default=0, null=True, blank=True)  # Qoo10　ショップの通し番号 my_shop_num
    glink = models.TextField('商品リンク', max_length=300, default='', null=True, blank=True)
    wow_lotno = models.IntegerField('wowロットナンバー', default=0, null=True, blank=True)  # wowmaに登録された商品のロットナンバー　535263333
    WOW_UPD_STATUS = ((0, '未登録'), (1, '掲載中'), (2, '登録済みだが未掲載'))
    wow_upd_status = models.IntegerField('wow掲載状況', choices=WOW_UPD_STATUS, default=0, null=True, blank=True) # wowmaの掲載ステータス
    WOW_STATUS = ((0, '確認待ち'), (1, 'OK'), (2, 'NG'), (3, '在庫切れ'))
    wow_on_flg = models.IntegerField('wowステータス', choices=WOW_STATUS, default=0, null=True, blank=True) # wowmaの出品ステータス　NG はブラックリスト
    wow_price = models.IntegerField('wowma価格', default=0, null=True, blank=True) # wowmaの価格
    wow_fixed_price = models.IntegerField('wowma固定価格', default=0, null=True, blank=True) # wowmaの固定価格。もしこれが0より大きければ優先される
    wow_postage_segment = models.IntegerField('送料設定区分', default=2, null=True, blank=True)  # wowmaの# 送料設定区分 1:送料別/2:送料込み/3:個別送料
    wow_postage = models.IntegerField('個別送料', default=0, null=True, blank=True)  # wowmaの個別送料
    wow_delivery_method_id = models.IntegerField('配送方法ID', default=0, null=True, blank=True)  # wowmaの配送方法ID
    QOO_UPD_STATUS = ((1, '取引待機'), (2, '取引可能'), (3, '取引廃止'))
    qoo_upd_status = models.IntegerField('qoo掲載状況', choices=QOO_UPD_STATUS, default=1, null=True, blank=True) # qooの掲載ステータス 取引待機= 1、取引可能= 2、取引廃止= 3）
    qoo_gdno = models.TextField('qoo商品コード', max_length=100, default='', null=True, blank=True) # 登録された商品のQoo10商品コード
    qoo_seller_code = models.TextField('qoo販売者コード', max_length=100, default='', null=True, blank=True) # qooの販売者独自のコード
    QOO_STATUS = ((0, '確認待ち'), (1, 'OK'), (2, 'NG'), (3, '在庫切れ'))
    qoo_on_flg = models.IntegerField('qooステータス', choices=QOO_STATUS, default=0, null=True, blank=True) # qooの出品ステータス　NG はブラックリスト
    qoo_price = models.IntegerField('qoo価格', default=0, null=True, blank=True) # qooの価格
    qoo_postage_segment = models.IntegerField('送料設定区分', default=2, null=True, blank=True)  # qooの# 送料設定区分 1:送料別/2:送料込み/3:個別送料
    qoo_fixed_price = models.IntegerField('qoo固定価格', default=0, null=True, blank=True) # qooの固定価格。もしこれが0より大きければ優先される
    qoo_shipping_no = models.IntegerField('qoo送料コード', default=0, null=True, blank=True)  # qooの送料コード 0:送料無料
    qoo_postage = models.IntegerField('qoo個別送料', default=0, null=True, blank=True)  # qooの個別送料
    qoo_delivery_method_id = models.IntegerField('qoo配送方法ID', default=0, null=True, blank=True)  # qooの配送方法ID
    qoo_item_qty = models.IntegerField('qoo商品数量', default=1, null=True, blank=True)  # qooの商品数量
    qoo_item_type = models.TextField('qoo商品タイプ', max_length=500, default='', null=True, blank=True)
    qoo_expire_date = models.DateTimeField('qoo商品の販売終了日', default=None, null=True, blank=True)
    create_date = models.DateTimeField('作成時間', default=timezone.now)
    update_date = models.DateTimeField('更新時間', auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<YaBuyersItemDetail:gid=' + str(self.gid) + ', ' + \
               'gname[' + self.gname + '] >'

    class Meta:
        verbose_name = 'バイヤーズ商品詳細(ショップ毎)'
        verbose_name_plural = 'バイヤーズ商品詳細(ショップ毎)'


# qoo10の受注情報
class QooOrderInfo(models.Model):
    order_no = models.IntegerField('orderNo', default=0, primary_key=True)  # id 注文番号
    shipping_status = models.TextField('shippingStatus', max_length=10, default='', null=True, blank=True)  # 配送状態
    seller_id = models.TextField('sellerID', max_length=20, default='', null=True, blank=True)  # 販売者ID
    pack_no = models.IntegerField('packNo', default=0)  # id カート番号
    order_date = models.TextField('orderDate', max_length=19, default='', null=True, blank=True)  # 注文日
    payment_date = models.TextField('PaymentDate', max_length=19, default='', null=True, blank=True)  # 決済日
    est_shipping_date = models.TextField('EstShippingDate', max_length=19, default='', null=True, blank=True)  # 発送予定日
    shipping_date = models.TextField('ShippingDate', max_length=19, default='', null=True, blank=True)  # 発送日
    delivered_date = models.TextField('DeliveredDate', max_length=19, default='', null=True, blank=True)  # 配送完了日
    buyer = models.TextField('buyer', max_length=100, default='', null=True, blank=True)  # 購入者名
    buyer_gata = models.TextField('buyer_gata', max_length=50, default='', null=True, blank=True)  # 購入者名（カタカナ）
    buyer_tel = models.TextField('buyerTel', max_length=17, default='', null=True, blank=True)  # 購入者の電話番号
    buyer_mobile = models.TextField('buyerMobile', max_length=17, default='', null=True, blank=True)  # 購入者の携帯電話番号
    buyer_email = models.TextField('buyerEmail', max_length=50, default='', null=True, blank=True)  # 購入者の携帯電話番号
    item_code = models.TextField('itemCode', max_length=9, default='', null=True, blank=True)  # Qoo10商品番号
    seller_item_code = models.TextField('sellerItemCode', max_length=50, default='', null=True, blank=True)  # 販売商品コード
    item_title = models.TextField('itemTitle', max_length=100, default='', null=True, blank=True)  # 商品名
    option = models.TextField('option', max_length=200, default='', null=True, blank=True)  # オプション
    option_code = models.TextField('optionCode', max_length=50, default='', null=True, blank=True)  # オプションコード
    order_price = models.IntegerField('orderPrice', default=0, null=True, blank=True)  # 商品価格
    order_qty = models.IntegerField('orderQty', default=0, null=True, blank=True)  # 注文数量
    discount = models.IntegerField('discount', default=0, null=True, blank=True)  # 商品割引金額
    total = models.IntegerField('total', default=0, null=True, blank=True)  # 注文数量（商品価格 + オプション価格 - 割引額）
    receiver = models.TextField('receiver', max_length=100, default='', null=True, blank=True)  # 受取人名
    receiver_gata = models.TextField('receiver_gata', max_length=100, default='', null=True, blank=True)  # 受取人名（カタカナ）
    shipping_country = models.TextField('shippingCountry', max_length=2, default='', null=True, blank=True)  # お届け先の国家
    zipcode = models.TextField('zipcode', max_length=10, default='', null=True, blank=True)  # 郵便番号
    shipping_addr = models.TextField('shippingAddr', max_length=100, default='', null=True, blank=True)  # お届け先住所
    addr1 = models.TextField('Addr1', max_length=100, default='', null=True, blank=True)  # 住所(都道府県/市区町村)
    addr2 = models.TextField('Addr2', max_length=100, default='', null=True, blank=True)  # 住所(市区町村以降)
    receiver_tel = models.TextField('receiverTel', max_length=17, default='', null=True, blank=True)  # 受取人の電話番号
    receiver_mobile = models.TextField('receiverMobile', max_length=17, default='', null=True, blank=True)  # 受取人の携帯電話番号
    hope_date = models.TextField('hopeDate', max_length=19, default='', null=True, blank=True)  # 配送希望日
    sender_name = models.TextField('senderName', max_length=50, default='', null=True, blank=True)  # 送信者
    sender_tel = models.TextField('senderTel', max_length=17, default='', null=True, blank=True)  # 送り主の電話番号
    sender_nation = models.TextField('senderNation', max_length=2, default='', null=True, blank=True)  # 送り主の国家
    sender_zipcode = models.TextField('senderZipCode', max_length=8, default='', null=True, blank=True)  # 送り主の郵便番号
    sender_addr = models.TextField('senderAddr', max_length=100, default='', null=True, blank=True)  # 送り主の住所
    shipping_way = models.TextField('ShippingWay', max_length=2, default='', null=True, blank=True)  # 配送方法
    shipping_msg = models.TextField('ShippingMsg', max_length=200, default='', null=True, blank=True)  # 配送メッセージ
    payment_method = models.TextField('PaymentMethod', max_length=15, default='', null=True, blank=True)  # 決済手段
    seller_discount = models.IntegerField('SellerDiscount', default=0, null=True, blank=True)  # 販売者負担割引額
    currency = models.TextField('Currency', max_length=3, default='', null=True, blank=True)  # 注文金額通貨
    shipping_rate = models.IntegerField('ShippingRate', default=0, null=True, blank=True)  # 送料
    related_order = models.TextField('RelatedOrder', max_length=330, default='', null=True,
                                    blank=True)  # 関連注文番号：（、）区切り文字で注文番号区分する。例）12345432、12343212、12323232
    shipping_rate_type = models.TextField('shippingRateType', max_length=18, default='', null=True,
                                        blank=True)  # 送料グループの種類：Free / Charge / Free on condition / Charge on delivery
    delivery_company = models.TextField('DeliveryCompany', max_length=30, default='', null=True, blank=True)  # 配送会社
    voucher_code = models.TextField('VoucherCode', max_length=100, default='', null=True, blank=True)  # 訪問受領認証番号
    packing_no = models.TextField('PackingNo', max_length=50, default='', null=True,
                                 blank=True)  # 発注時に生成されるパッキング番号（例：JPP22894429）
    seller_delivery_no = models.TextField('SellerDeliveryNo', max_length=50, default='', null=True,
                                        blank=True)  # 発注時に生成されるパッキング番号と1：1でマッチングされる販売者単位のシリアル番号（例：130705-0003）
    payment_nation = models.TextField('PaymentNation', max_length=2, default='', null=True, blank=True)  # 注文サイト国：JP
    gift = models.TextField('Gift', max_length=100, default='', null=True, blank=True)  # 贈答品（ギフト、プレゼント、おまけ）
    cod_price = models.IntegerField('cod_price', default=0, null=True, blank=True)  # 着払い決済金額
    cart_discount_seller = models.IntegerField('Cart_Discount_Seller', default=0, null=True,
                                            blank=True)  # 販売者負担カート割引
    cart_discount_qoo10 = models.IntegerField('Cart_Discount_Qoo10', default=0, null=True,
                                           blank=True)  # Qoo10負担カート割引
    settle_price = models.IntegerField('SettlePrice', default=0, null=True, blank=True)  # 総供給原価
    branch_name = models.TextField('BranchName', max_length=50, default='', null=True, blank=True)  # 支店名
    tracking_no = models.TextField('TrackingNo', max_length=50, default='', null=True, blank=True)  # 送り状番号
    oversea_consignment = models.TextField('OverseaConsignment', max_length=1, default='', null=True,
                                          blank=True)  # 海外委託 (Y/N)
    oversea_consignment_receiver = models.TextField('OverseaConsignment_receiver', max_length=100, default='', null=True,
                                                   blank=True)  # 海外委託受取人
    oversea_consignment_country = models.TextField('OverseaConsignment_Country', max_length=2, default='', null=True,
                                                  blank=True)  # 海外委託国家
    oversea_consignment_zipcode = models.TextField('OverseaConsignment_zipCode', max_length=8, default='', null=True,
                                                  blank=True)  # 海外委託 郵便番号
    oversea_consignment_addr1 = models.TextField('OverseaConsignment_Addr1', max_length=100, default='', null=True,
                                                blank=True)  # 海外委託 住所(都道府県/市区町村)
    oversea_consignment_addr2 = models.TextField('OverseaConsignment_Addr2', max_length=100, default='', null=True,
                                                blank=True)  # 海外委託 住所(市区町村以降)
    delay_type = models.TextField('DelayType', max_length=1, default='', null=True, blank=True)  # 遅延の理由。（1：商品準備中、2：注文製作（オーダーメイド）、3：顧客の要求、4：その他）
    delay_memo = models.TextField('DelayMemo', max_length=1000, default='', null=True, blank=True)  # 販売者メモ
    # 以下はバイヤーズで発注かけた際の履歴
    buyers_order_no = models.TextField('バイヤーズ注文番号', max_length=30, default='', null=True, blank=True) #バイヤーズ注文番号

    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<QooOrderInfo:order_no=' + str(self.order_no) + '>'

    class Meta:
        verbose_name = 'qoo10受注情報'
        verbose_name_plural = 'qoo10受注情報'


class QooBuyersOrderDetail(models.Model):
    buyers_order_id = models.CharField('バイヤーズ注文番号', max_length=30, default='', primary_key=True)  # バイヤーズ注文番号
    order_detail = models.ForeignKey(QooOrderInfo, on_delete=models.CASCADE)  # 注文詳細の親 QooOrderInfo）Foreign key
    status = models.TextField('状況', max_length=30, default='', null=True, blank=True)  # 状況
    PAYMENT_METHOD = ((0, 'ポイント支払い'), (1, 'au pay'), (2, 'クレジットカード'), (3, 'ゆうちょ振り込み'))
    payment_method = models.IntegerField('支払い方法', choices=PAYMENT_METHOD, default=0, null=True, blank=True)  # 支払い方法
    payment_total = models.IntegerField('支払い合計金額', default=0, null=True, blank=True)  # 支払い合計金額
    delivery_method = models.TextField('配送方法', max_length=100, default='', null=True, blank=True)  # 配送方法
    shipping_no = models.TextField('伝票番号', max_length=100, default='', null=True, blank=True)  # 伝票番号
    au_pay_id = models.IntegerField('AuPay支払いID', default=0, null=True, blank=True)  # au pay支払いID
    order_date = models.TextField('注文日', max_length=50, default='', null=True, blank=True)  # 注文日
    payment_chk_date = models.TextField('入金確認日', max_length=50, default='', null=True, blank=True)  # 入金確認日
    shipped_date = models.TextField('発送日', max_length=50, default='', null=True, blank=True)  # 発送日
    memo = models.TextField('備考', max_length=500, default='', null=True, blank=True)  # 備考
    unit = models.IntegerField('注文個数', default=0, null=True, blank=True)  # 注文個数
    create_date = models.DateTimeField('作成日', default=timezone.now)
    update_date = models.DateTimeField('更新日', auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<QooBuyersOrderDetail:buyers_order_id=[' + str(self.buyers_order_id) + '] >'

    class Meta:
        verbose_name = 'qoo10からのバイヤーズ注文詳細'
        verbose_name_plural = 'qoo10からのバイヤーズ注文詳細'


# wowmaの受注情報 3つのモデルは以下参考に
# https://y-hilite.com/3236/
class WowmaOrderInfo(models.Model):
    orderid = models.IntegerField('注文ID', default=0, primary_key=True) # orderid
    shop_id = models.IntegerField('WowmaショップID', default=0, null=True, blank=True) # WowmaショップID
    sell_method_segment = models.TextField('販売方法区分', max_length=1, default='', null=True, blank=True) # sellMethodSegment
    release_date = models.TextField(max_length=10, default='', null=True, blank=True) # 発売(入荷)予定日
    site_and_device = models.TextField('サイトや端末', max_length=100, default='', null=True, blank=True) # site and device
    cross_border_ec_trade_kbn = models.TextField('越境EC取引区分', max_length=1, default='', null=True, blank=True) # crossBorderEcTradeKbn
    mail_address = models.TextField('メールアドレス', max_length=128, default='', null=True, blank=True) # mailaddress
    raw_mail_address = models.TextField('非暗号化メールアドレス', max_length=128, default='', null=True, blank=True) # rawMailAddress
    order_name = models.TextField('注文者氏名', max_length=50, default='', null=True, blank=True) # 注文者氏名
    order_kana = models.TextField('注文者かな', max_length=50, default='', null=True, blank=True) # order_kana
    order_zipcode = models.TextField('郵便番号', max_length=10, default='', null=True, blank=True) # order_zipcode
    order_address = models.TextField('注文者住所', max_length=300, default='', null=True, blank=True) # order_address
    order_phone_number_1 = models.TextField('注文者電話番号_1', max_length=15, default='', null=True, blank=True) # order_phone_number_1
    order_phone_number_2 = models.TextField('注文者電話番号_2', max_length=15, default='', null=True, blank=True) # order_zipcode
    nickname = models.TextField('ニックネーム', max_length=30, default='', null=True, blank=True) # nickname
    sender_name = models.TextField(max_length=50, default='', null=True, blank=True) # 送付先氏名
    sender_kana = models.TextField(max_length=50, default='', null=True, blank=True) # 送付先かな
    sender_zipcode = models.TextField(max_length=10, default='', null=True, blank=True) # 送付先zipcode
    sender_address = models.TextField(max_length=300, default='', null=True, blank=True) # 送付先住所
    sender_phone_number_1 = models.TextField(max_length=15, default='', null=True, blank=True) # 送付先_電話番号_1
    sender_phone_number_2 = models.TextField(max_length=15, default='', null=True, blank=True) # 送付先_電話番号_2
    sender_shop_cd = models.TextField(max_length=4, default='', null=True, blank=True) # 送付先店舗コード
    order_option = models.TextField(max_length=30, default='', null=True, blank=True) # 注文オプション
    settlement_name = models.TextField(max_length=30, default='', null=True, blank=True) # 決済方法
    secure_segment = models.TextField(max_length=1, default='', null=True, blank=True) # 3Dセキュア利用区分
    user_comment = models.TextField(max_length=300, default='', null=True, blank=True) # ユーザコメント
    trade_remarks = models.TextField(max_length=162, default='', null=True, blank=True) # 特記事項
    memo = models.TextField(max_length=200, default='', null=True, blank=True) # メモ
    order_status = models.TextField(max_length=15, default='', null=True, blank=True) # order_ステータス
    contact_status = models.TextField(max_length=5, default='', null=True, blank=True) # コンタクト_ステータス
    authorization_status = models.TextField(max_length=5, default='', null=True, blank=True) # 承認_ステータス
    payment_status = models.TextField(max_length=5, default='', null=True, blank=True) # 支払い_ステータス
    ship_status = models.TextField(max_length=5, default='', null=True, blank=True) # 発送_ステータス
    print_status = models.TextField(max_length=5, default='', null=True, blank=True) # 印刷_ステータス
    cancel_status = models.TextField(max_length=5, default='', null=True, blank=True) # キャンセル_ステータス
    cancel_reason = models.TextField(max_length=100, default='', null=True, blank=True) # キャンセル理由
    cancel_comment = models.TextField(max_length=100, default='', null=True, blank=True) # キャンセルコメント
    total_sale_price = models.IntegerField(default=0, null=True, blank=True) # 売上金額合計
    total_sale_price_normal_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]販売総額(10%)
    total_sale_price_reduced_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]販売総額(8%)
    total_sale_price_no_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]販売総額(0%)
    total_sale_unit = models.IntegerField(default=0, null=True, blank=True) # 売上個数合計
    postage_price = models.IntegerField(default=0, null=True, blank=True) # 送料
    postage_price_tax_rate = models.FloatField(default=0, null=True, blank=True) # 送料税率
    charge_price = models.IntegerField(default=0, null=True, blank=True) # 請求金額
    charge_price_tax_rate = models.FloatField(default=0, null=True, blank=True) # 手数料税率
    total_item_option_price = models.IntegerField(default=0, null=True, blank=True) # オプション手数料(合計)
    total_item_option_price_tax_rate = models.FloatField(default=0, null=True, blank=True) # オプション手数料(合計)税率
    total_gift_wrapping_price = models.IntegerField(default=0, null=True, blank=True) # ギフト手数料(合計)
    total_gift_wrapping_price_tax_rate = models.FloatField(default=0, null=True, blank=True) # ギフト手数料(合計)税率
    total_price = models.IntegerField(default=0, null=True, blank=True) # 総合計金額
    total_price_normal_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]請求金額小計(10%)
    total_price_reduced_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]請求金額小計(8%)
    total_price_no_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]請求金額小計(0%)
    premium_type = models.IntegerField(default=0, null=True, blank=True) # auスマートパスプレミアム特典プログラム適用区分
    premium_issue_price = models.IntegerField(default=0, null=True, blank=True) # auスマートパスプレミアム特典プログラム適用金額
    premium_mall_price = models.IntegerField(default=0, null=True, blank=True) # モール負担送料
    premium_shop_price = models.IntegerField(default=0, null=True, blank=True) # 店舗様負担送料
    coupon_total_price = models.IntegerField(default=0, null=True, blank=True) # クーポン利用合計金額
    coupon_total_price_normal_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]クーポン利用額(10%)
    coupon_total_price_reduced_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]クーポン利用額(8%)
    coupon_total_price_no_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]クーポン利用額(0%)
    use_point = models.IntegerField(default=0, null=True, blank=True) # 利用ポイント
    use_point_normal_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]ポイント利用額(10%)
    use_point_reduced_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]ポイント利用額(10%)
    use_point_no_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]ポイント利用額(10%)
    use_point_cancel = models.TextField(max_length=5, default='', null=True, blank=True) # 利用ポイント キャンセル分
    use_au_point_price = models.IntegerField(default=0, null=True, blank=True) # au利用ポイント金額
    use_au_point_price_normal_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]auポイント・Pontaポイント（au PAY マーケット限定含む）利用額(10%)
    use_au_point_price_reduced_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]auポイント・Pontaポイント（au PAY マーケット限定含む）利用額(8%)
    use_au_point_price_no_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]auポイント・Pontaポイント（au PAY マーケット限定含む）利用額(0%)
    use_au_point = models.IntegerField(default=0, null=True, blank=True) # au利用ポイント
    use_au_point_cancel = models.TextField(max_length=5, default='', null=True, blank=True) # au利用ポイント キャンセル分
    request_price = models.IntegerField(default=0, null=True, blank=True) # 請求金額
    request_price_normal_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]請求金額(10%)
    request_price_reduced_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]請求金額(8%)
    request_price_no_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]請求金額(0%)
    point_fixed_date = models.TextField(max_length=20, default='', null=True, blank=True) # 付与ポイント確定(予定)日
    point_fixed_status = models.TextField(max_length=5, default='', null=True, blank=True) # ポイント fixステータス
    settle_status = models.TextField(max_length=2, default='', null=True, blank=True) # 承認ステータス
    authori_timelimit_date = models.TextField(max_length=10, default='', null=True, blank=True) # オーソリ期日
    pg_result = models.TextField(max_length=1, default='', null=True, blank=True) # 決済結果
    pg_response_code = models.TextField(max_length=5, default='', null=True, blank=True) # 決済結果コード
    pg_response_detail = models.TextField(max_length=384, default='', null=True, blank=True) # 決済結果詳細
    pg_orderid = models.TextField(max_length=20, default='', null=True, blank=True)  # pg_orderid
    pg_request_price = models.IntegerField(default=0, null=True, blank=True) # pg_請求金額
    pg_request_price_normal_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]決済請求金額(10%)
    pg_request_price_reduced_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]決済請求金額(8%)
    pg_request_price_no_tax = models.IntegerField(default=0, null=True, blank=True) # [内訳]決済請求金額(0%)
    coupon_type = models.TextField(max_length=5, default='', null=True, blank=True) # クーポンタイプ
    coupon_key = models.TextField(max_length=30, default='', null=True, blank=True) # クーポンキー
    card_jagdement = models.IntegerField(default=0, null=True, blank=True) # カード判定
    delivery_name = models.TextField(max_length=30, default='', null=True, blank=True) # 配送名
    delivery_method_id = models.TextField(max_length=10, default='', null=True, blank=True) # 配送方法id
    delivery_id = models.TextField(max_length=10, default='', null=True, blank=True) # (旧)配送方法ID
    elec_receipt_issue_status = models.TextField(max_length=1, default='', null=True, blank=True) # 電子領収書発行状況
    elec_receipt_issue_times = models.TextField(max_length=1, default='', null=True, blank=True) # 電子領収書発行回数
    delivery_request_day = models.TextField(max_length=20, default='', null=True, blank=True) # お届け希望日
    delivery_request_time = models.TextField(max_length=80, default='', null=True, blank=True) # お届希望時間帯
    shipping_carrier = models.TextField(max_length=1, default='', null=True, blank=True) # 配送業者
    shipping_number = models.TextField(max_length=15, default='', null=True, blank=True) # 追跡番号
    yamato_lnk_mgt_no = models.TextField(max_length=70, default='', null=True, blank=True) # B2クラウド連携管理番号

    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(auto_now=True, null=True, blank=True)
    order_date = models.DateTimeField(default=None, null=True, blank=True)  # 受注日
    contact_date = models.TextField(max_length=20, default='', null=True, blank=True)   # コンタクトした日
    authorization_date = models.TextField(max_length=20, default='', null=True, blank=True)   # 承認日
    payment_date = models.TextField(max_length=20, default='', null=True, blank=True)   # 支払い日
    ship_date = models.TextField(max_length=20, default='', null=True, blank=True)   # 発送日
    print_date = models.TextField(max_length=20, default='', null=True, blank=True)   # 印刷日
    cancel_date = models.TextField(max_length=20, default='', null=True, blank=True)   # キャンセル日
    shipping_date = models.TextField(max_length=20, default='', null=True, blank=True)   # 配送日

    # 注文全体の管理をする。個別での発送など完了してからこちらも変える
    """
    1. wow注文が入る、何もしてない
    2. Amaで注文を入れている状態。logiには入荷依頼をかけていい。全部の入荷依頼は終わってない状態
       注文番号をgetして注文詳細側WowmaOrderDetailに保持。
       wowはこの時点で注文承認とする
       全部の商品が注文できたら、注文単位のステータスも更新される
    3. ★logiで入荷依頼をかけている状態。
       注文単位で他が発注できてなくても、個別に入荷依頼しておかないといけない
    4. ★全部の注文に対して入荷依頼をかけ終えた状態
       出荷待ちだったが出荷されたのでデータを取ってきて保持。これも個別にやる
    5. logiで出荷されたらwowに発送済みとするが、これは個別でできれば。
       完了にするのは商品単位すべてが発送まで完了して初めて完了となる。
    6. ★なんかのエラーステータス
    """
    order_all_status = models.IntegerField(default=1, null=True, blank=True)

    def __str__(self):
        return '<WowmaOrderInfo:orderid=' + str(self.orderid) + '>'

    class Meta:
        verbose_name = 'wowma受注情報'
        verbose_name_plural = 'wowma受注情報'


# wowmaの受注情報 (個別の詳細）
class WowmaOrderDetail(models.Model):
    order_detail_id = models.IntegerField('注文詳細ID', default=0, primary_key=True) # order_detail_id （詳細のid）
    orderinfo = models.ForeignKey(WowmaOrderInfo, on_delete=models.CASCADE) # 注文の親 WowmaOrderInfo）Foreign key
    #orderinfo = models.IntegerField(default=0) # 注文の親 WowmaOrderInfo）Foreign key
    item_management_id = models.TextField(max_length=100, default='', null=True, blank=True) # 管理用ID
    item_code = models.TextField(max_length=50, default='', null=True, blank=True) # 商品コード
    lot_number = models.TextField(max_length=50, default='', null=True, blank=True) # ロットナンバー
    item_name = models.TextField(max_length=300, default='', null=True, blank=True) # 商品名。gname と同じ
    item_option = models.TextField(max_length=300, default='', null=True, blank=True) # オプション情報
    item_option_price = models.IntegerField(default=0, null=True, blank=True) # オプション手数料
    gift_wrapping_type = models.TextField(max_length=20, default='', null=True, blank=True) #　ギフト包装種別
    gift_wrapping_price = models.IntegerField(default=0, null=True, blank=True) # ギフト手数料
    gift_message = models.TextField(max_length=200, default='', null=True, blank=True) #　ギフトメッセージ
    noshi_type = models.TextField(max_length=20, default='', null=True, blank=True) #　のし種別
    noshi_presenter_name1 = models.TextField(max_length=100, default='', null=True, blank=True) #　のし贈り主名1
    noshi_presenter_name2 = models.TextField(max_length=100, default='', null=True, blank=True) #　のし贈り主名2
    noshi_presenter_name3 = models.TextField(max_length=100, default='', null=True, blank=True) #　のし贈り主名3
    item_cancel_status = models.TextField(max_length=5, default='', null=True, blank=True) #　キャンセルステータス
    item_cancel_date = models.TextField(max_length=20, default='', null=True, blank=True)  # 取引明細キャンセル日時
    before_discount = models.IntegerField(default=0, null=True, blank=True) # 値引き前金額
    discount = models.IntegerField(default=0, null=True, blank=True) # 値引き額
    item_price = models.IntegerField(default=0, null=True, blank=True) # 商品代金
    unit = models.IntegerField(default=0, null=True, blank=True) # 注文個数
    total_item_price = models.IntegerField(default=0, null=True, blank=True) # 商品代金 合計
    total_item_charge_price = models.IntegerField(default=0, null=True, blank=True) # 商品代金 合計
    tax_type = models.TextField(max_length=1, default='', null=True, blank=True) #　消費税区分
    reduced_tax = models.TextField(max_length=1, default='', null=True, blank=True) #　軽減税率設定
    tax_rate = models.TextField(max_length=5, default='', null=True, blank=True) #　消費税率
    gift_point = models.IntegerField(default=0, null=True, blank=True) # ギフト代金
    shipping_day_disp_text = models.TextField(max_length=40, default='', null=True, blank=True) #発送日表示文言
    shipping_time_limit_date = models.TextField(max_length=10, default='', null=True, blank=True) #発送期限日
    # 以下はバイヤーズで発注かけた際の履歴
    # buyers_order_no = models.TextField('バイヤーズ注文番号', max_length=30, default='', null=True, blank=True) #バイヤーズ注文番号
    # Amazonで発注した履歴関連
    ama_order_no = models.TextField('Amazon注文番号', max_length=30, default='', null=True, blank=True)
    ama_order_date = models.DateTimeField('Amazon注文日時', default=None, null=True, blank=True)
    # logispi関連
    logi_order_no = models.TextField('ロジスピ注文番号', max_length=50, default='', null=True, blank=True)
    logi_order_amount = models.IntegerField('ロジスピ注文数量', default=0, null=True, blank=True)
    logi_shipped_date = models.DateTimeField('ロジスピ発送日', default=None, null=True, blank=True)
    logi_sender_name = models.TextField('ロジスピ発送先宛名', max_length=50, default='', null=True, blank=True) # 送付先氏名
    logi_sender_zipcode = models.TextField('ロジスピ発送先郵便番号', max_length=10, default='', null=True, blank=True) # 送付先zipcode
    logi_sender_address = models.TextField('ロジスピ発送先住所', max_length=300, default='', null=True, blank=True) # 送付先住所
    logi_sender_phone_number = models.TextField('ロジスピ発送先電話番号', max_length=15, default='', null=True, blank=True) # 送付先_電話番号_1
    logi_order_option = models.TextField('ロジスピ発送先オプション', max_length=200, default='', null=True, blank=True) # 注文オプション
    logi_order_shipping_time = models.TextField('ロジスピ発送先配送時間帯', max_length=100, default='', null=True, blank=True) # 注文オプション
    logi_order_identifier = models.TextField('ロジスピ配送元の識別名', max_length=50, default='', null=True, blank=True) # 注文オプション
    logi_is_postbin = models.IntegerField('ロジスピポスト便希望', default=0, null=True, blank=True)  # 0:ポスト便じゃない/ 1:ポスト便希望

    # 自分の処理ステータス。要注意
    """
    1. wow注文が入る、何もしてない
    2. Amaで注文を入れた状態。> 注文番号をgetして保持。この時点でwowには注文承認とする
    3. ★Amaで注文を入れたものに対して、logiで入荷依頼をかけた状態
    4. ★入荷依頼をかけて出荷待ちだったが出荷されたのでデータを取ってきて保持した状態
    5. logiで出荷された状態。wowに発送済みとする。完了にしていいかな
    6. ★なんかのエラーステータス
    """
    order_detail_status = models.IntegerField(default=1, null=True, blank=True)
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<WowmaOrderDetail:orderdetailid=[' + str(self.order_detail_id) + '] >'

    class Meta:
        verbose_name = 'wowma受注詳細'
        verbose_name_plural = 'wowma受注詳細'


class WowmaBuyersOrderDetail(models.Model):
    buyers_order_id = models.CharField('バイヤーズ注文番号', max_length=30, default='', primary_key=True)  #バイヤーズ注文番号
    order_detail = models.ForeignKey(WowmaOrderDetail, on_delete=models.CASCADE)  # 注文詳細の親 WowmaOrderDetail）Foreign key
    status = models.TextField('状況', max_length=30, default='', null=True, blank=True)  # 状況
    PAYMENT_METHOD = ((0, 'ポイント支払い'), (1, 'au pay'), (2, 'クレジットカード'), (3, 'ゆうちょ振り込み'))
    payment_method = models.IntegerField('支払い方法', choices=PAYMENT_METHOD, default=0, null=True, blank=True)  # 支払い方法
    payment_total = models.IntegerField('支払い合計金額', default=0, null=True, blank=True)  # 支払い合計金額
    delivery_method = models.TextField('配送方法', max_length=100, default='', null=True, blank=True)  # 配送方法
    shipping_no = models.TextField('伝票番号', max_length=100, default='', null=True, blank=True)  # 伝票番号
    au_pay_id = models.IntegerField('AuPay支払いID', default=0, null=True, blank=True)  # au pay支払いID
    order_date = models.TextField('注文日', max_length=50, default='', null=True, blank=True)  # 注文日
    payment_chk_date = models.TextField('入金確認日', max_length=50, default='', null=True, blank=True)  # 入金確認日
    shipped_date = models.TextField('発送日', max_length=50, default='', null=True, blank=True)  # 発送日
    memo = models.TextField('備考', max_length=500, default='', null=True, blank=True)  # 備考
    unit = models.IntegerField('注文個数', default=0, null=True, blank=True)  # 注文個数
    create_date = models.DateTimeField('作成日', default=timezone.now)
    update_date = models.DateTimeField('更新日', auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<WowmaBuyersOrderDetail:buyers_order_id=[' + str(self.buyers_order_id) + '] >'

    class Meta:
        verbose_name = 'wowmaからのバイヤーズ注文詳細'
        verbose_name_plural = 'wowmaからのバイヤーズ注文詳細'

# qoo10とwowmaの受注情報をミックス（
class AllOrderInfo(models.Model):
    id = models.AutoField('ID', primary_key=True)  # id
    qoo_id = models.ForeignKey(QooOrderInfo, null=True, blank=True, on_delete=models.CASCADE)
    wow_id = models.ForeignKey(WowmaOrderInfo, null=True, blank=True, on_delete=models.CASCADE)

    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<AllOrderInfo:id=' + str(self.id) + '>'

    class Meta:
        verbose_name = '受注情報全て'
        verbose_name_plural = '受注情報全て'

# qoo10のショップ登録情報
class QooShopInfo(models.Model):
    my_shop_num = models.IntegerField('ショップ番号', default=0, primary_key=True)  # Qoo10　ショップの通し番号
    shop_name = models.TextField('ショップ名', max_length=100, default='')  # Qoo10　ショップ名
    auth_key = models.TextField('認証キー', max_length=300, default='')
    user_id = models.TextField('ユーザID', max_length=300, default='')
    pwd = models.TextField('パスワード', max_length=300, default='')
    target_url = models.TextField('ターゲットURL', max_length=300, default='')
    from_name = models.TextField('発送元名称', max_length=100, default='')  # Qoo10　発送元ショップ名もしくは個人名
    from_name_kana = models.TextField('発送元名称カタカナ', max_length=100, default='')  # Qoo10　発送元ショップ名もしくは個人名カタカナ
    from_postcode = models.TextField('発送元郵便番号', max_length=10, default='')  # Qoo10　発送元郵便番号
    from_state = models.TextField('発送元都道府県', max_length=10, default='')  # Qoo10　発送元都道府県
    from_address_1 = models.TextField('発送元住所1', max_length=100, default='')  # Qoo10　発送元住所1
    from_address_2 = models.TextField('発送元住所2', max_length=100, default='', null=True, blank=True)  # Qoo10　発送元住所2
    from_phone = models.TextField('発送元電話番号', max_length=20, default='')  # Qoo10　発送元電話番号
    mail = models.TextField('メールアドレス', max_length=50, default='')  # 発送元メールアドレス
    SHOP_STATUS = ((0, '閉店中'), (1, '開店中'))
    shop_status = models.IntegerField('ショップ開店状況', choices=SHOP_STATUS, default=0, null=True, blank=True)  # ショップ開店状況
    create_date = models.DateTimeField('作成時間', default=timezone.now)
    update_date = models.DateTimeField('更新時間', auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<QooShopInfo:my_shop_num=' + str(self.my_shop_num) + '>'

    class Meta:
        verbose_name = 'qoo10のショップ登録情報'
        verbose_name_plural = 'qoo10のショップ登録情報'


# wowmaのショップ登録情報
# Todo: ショップ毎の配送情報をここに持つか。
class WowmaShopInfo(models.Model):
    my_shop_num = models.IntegerField('ショップ番号', default=0, primary_key=True)  # wowma　ショップの通し番号
    shop_id = models.IntegerField('ショップID', default=0, )  # wowma　ショップの通し番号
    shop_name = models.TextField('ショップ名', max_length=100, default='')  # wowma　ショップ名
    api_key = models.TextField('apiキー', max_length=300, default='')
    target_url = models.TextField('ターゲットURL', max_length=300, default='')
    from_name = models.TextField('発送元名称', max_length=100, default='')  # wowma　発送元ショップ名もしくは個人名
    from_name_kana = models.TextField('発送元名称カタカナ', max_length=100, default='')  # Qoo10　発送元ショップ名もしくは個人名カタカナ
    from_postcode = models.TextField('発送元郵便番号', max_length=10, default='')  # wowma　発送元郵便番号
    from_state = models.TextField('発送元都道府県', max_length=10, default='')  # wowma　発送元都道府県
    from_address_1 = models.TextField('発送元住所1', max_length=100, default='')  # wowma　発送元住所1
    from_address_2 = models.TextField('発送元住所2', max_length=100, default='', null=True, blank=True)  # wowma　発送元住所2
    from_phone = models.TextField('発送元電話番号', max_length=20, default='')  # wowma　発送元電話番号
    mail = models.TextField('メールアドレス', max_length=50, default='')  # wowma　発送元メールアドレス
    SHOP_STATUS = ((0, '閉店中'), (1, '開店中'))
    shop_status = models.IntegerField('ショップ開店状況', choices=SHOP_STATUS, default=0, null=True, blank=True)  # ショップ開店状況
    create_date = models.DateTimeField('作成時間', default=timezone.now)
    update_date = models.DateTimeField('更新時間', auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<WowmaShopInfo:shop_id=' + str(self.shop_id) + '>'

    class Meta:
        verbose_name = 'wowmaのショップ登録情報'
        verbose_name_plural = 'wowmaのショップ登録情報'

# バッチ実行状況
class BatchStatus(models.Model):
    batch_id = models.AutoField('バッチ処理番号', primary_key=True)  # Qoo10　ショップの通し番号
    batch_name = models.TextField('バッチ名', max_length=1000, default='', null=True, blank=True)  # Qoo10　ショップ名
    message = models.TextField('メッセージ', max_length=10000, default='', null=True, blank=True)  # エラーメッセージなど
    BATCH_STATUS = ((0, '実行中'), (1, '正常終了'), (2, '異常終了'))
    batch_status = models.IntegerField('バッチ実行状況', choices=BATCH_STATUS, default=0, null=True, blank=True)  # バッチ実行状況
    start_date = models.DateTimeField('開始時刻', null=True, blank=True)
    end_date = models.DateTimeField('終了時刻', null=True, blank=True)
    stop_date = models.DateTimeField('中止時刻', null=True, blank=True)
    create_date = models.DateTimeField('作成時刻', default=timezone.now)
    update_date = models.DateTimeField('更新時刻', auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<BatchStatus:batch_id=' + str(self.batch_id) + '>'

    class Meta:
        verbose_name = 'バッチ実行状況'
        verbose_name_plural = 'バッチ実行状況'

# 処理中にエラーになった商品の情報をメモしておく
class ErrorGoodsLog(models.Model):
    id = models.AutoField('処理番号', primary_key=True)  # 処理番号
    batch_name = models.TextField('バッチ名', max_length=500, default='', null=True, blank=True)  # バッチや処理元のプログラム名
    asin = models.CharField('asin', max_length=30, default='', null=True, blank=True)  # asin
    status = models.IntegerField('バッチ実行状況', default=0, null=True, blank=True)  # ステータス
    code = models.TextField('リターンコード', default='', null=True, blank=True)  # リターンコード
    message = models.TextField('メッセージ', max_length=10000, default='', null=True, blank=True)  # エラーメッセージなど
    create_date = models.DateTimeField('作成時刻', default=timezone.now)
    update_date = models.DateTimeField('更新時刻', auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<ErrorGoodsLog:id=' + str(self.id) + '>'

    class Meta:
        verbose_name = '処理中にエラーになった商品の情報'
        verbose_name_plural = '処理中にエラーになった商品の情報'


class Eb_ItemStock(models.Model):
    item_no = models.TextField(max_length=20, default='')
    title = models.TextField(max_length=300, default='')
    custom_label = models.TextField(max_length=300, default='')
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(default=timezone.now)
    target_site = models.TextField(max_length=2, default='')
    delete_flg = models.BooleanField()


# buymaのバイヤー情報を格納する
class BuymaBuyersList(models.Model):
    b_id = models.IntegerField(default=0, primary_key=True)  # buymaのバイヤーid
    b_name = models.TextField(max_length=100, default='') # バイヤーの名称
    b_list_url = models.TextField(max_length=300, default='', null=True, blank=True) # バイヤーの個人ページURL
    good_cnt = models.IntegerField(default=0, null=True, blank=True)  # バイヤーの満足度高評価数
    reg_cnt = models.IntegerField(default=0, null=True, blank=True)  # 商品登録点数
    asos_reg_cnt = models.IntegerField(default=0, null=True, blank=True)  # ASOS 商品登録点数
    b_cat = models.IntegerField(default=0, null=True, blank=True)  # バイヤーの登録カテゴリ（個人1 かプレミアム 2かshop 3か）

    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return '<BuymaBuyersList:id=' + str(self.id) + ', ' + \
               'gid[' + self.gid + '] glink[' + self.glink + '] >'

    class Meta:
        verbose_name = 'buymaのバイヤー情報'
        verbose_name_plural = 'buymaのバイヤー情報'

# wowmaのタグリスト　カテゴリからタグリスト（親）の一覧を紐付ける
class WowmaCatTagOyaList(models.Model):
    wow_cat_id = models.IntegerField('wowmaカテゴリID', primary_key=True)  #wowmaカテゴリID
    cat_name = models.TextField('カテゴリ名', max_length=300, default='', null=True, blank=True)  #カテゴリ名
    tag_grp = models.TextField('タググループ', max_length=300, default='', null=True, blank=True)  # タググループ 半角スペース区切り
    create_date = models.DateTimeField('作成日', null=True, blank=True, default=timezone.now)
    update_date = models.DateTimeField('更新日', auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<WowmaCatTagOyaList:wow_cat_id=[' + str(self.wow_cat_id) + '] >'

    class Meta:
        verbose_name = 'wowmaのタグリスト'
        verbose_name_plural = 'wowmaのタグリスト'

# wowmaのタグリスト　親と子の組み合わせ
class WowmaTagChildList(models.Model):
    id = models.AutoField('ID', primary_key=True)  # id
    oya_id = models.IntegerField('親タグid', default=0, null=True, blank=True) # 親タグid
    oya_name = models.TextField('親タグ名称', max_length=100, default='', null=True, blank=True) # 親タグ名称
    child_name = models.TextField('子タグ名称', max_length=100, default='', null=True, blank=True) # 子タグ名称
    child_id = models.IntegerField('子タグid', default=0, null=True, blank=True) # 子タグid
    rel_flg = models.IntegerField('複数の子タグを登録できるか', default=0, null=True, blank=True) # 複数の子タグを登録できるか

    create_date = models.DateTimeField('作成日', null=True, blank=True, default=timezone.now)
    update_date = models.DateTimeField('更新日', auto_now=True, null=True, blank=True)

    def __str__(self):
        return '<WowmaTagChildList:id=' + str(self.id) + '>'

    class Meta:
        verbose_name = 'wowmaのタグリスト　親と子の組み合わせ'
        verbose_name_plural = 'wowmaのタグリスト　親と子の組み合わせ'


class QooAsinDetail(models.Model):
    # Qoo10用ASINによる情報を全て網羅してみる。

    asin = models.CharField(max_length=12, primary_key=True)
    title = models.TextField(max_length=300, default='')
    url = models.URLField(null=True, blank=True)
    amount = models.IntegerField(null=True, blank=True, default=0)  # 在庫数
    binding = models.TextField(max_length=200, null=True, blank=True, default='')
    brand = models.TextField(max_length=100, null=True, blank=True, default='')
    color = models.TextField(max_length=500, null=True, blank=True, default='')  # カラー
    department = models.TextField(max_length=200, null=True, blank=True, default='')
    is_adlt = models.BooleanField(null=True, blank=True, default=False)
    i_height = models.FloatField(null=True, blank=True, default=0)
    i_height_unit = models.TextField(null=True, blank=True, max_length=10, default='')
    i_length = models.FloatField(null=True, blank=True, default=0)
    i_length_unit = models.TextField(null=True, blank=True, max_length=10, default='')
    i_width = models.FloatField(null=True, blank=True, default=0)
    i_width_unit = models.TextField(null=True, blank=True, max_length=10, default='')
    i_weight = models.FloatField(null=True, blank=True, default=0)
    i_weight_unit = models.TextField(null=True, blank=True, max_length=10, default='')
    p_height = models.FloatField(null=True, blank=True, default=0)
    p_height_unit = models.TextField(null=True, blank=True, max_length=10, default='')
    p_length = models.FloatField(null=True, blank=True, default=0)
    p_length_unit = models.TextField(null=True, blank=True, max_length=10, default='')
    p_width = models.FloatField(null=True, blank=True, default=0)
    p_width_unit = models.TextField(null=True, blank=True, max_length=10, default='')
    p_weight = models.FloatField(null=True, blank=True, default=0)
    p_weight_unit = models.TextField(null=True, blank=True, max_length=10, default='')
    rank_cat_1 = models.TextField(max_length=100, null=True, blank=True, default='')
    rank_1 = models.IntegerField(null=True, blank=True, default=0)
    rank_cat_2 = models.TextField(max_length=100, null=True, blank=True, default='')
    rank_2 = models.IntegerField(null=True, blank=True, default=0)
    rank_cat_3 = models.TextField(max_length=100, null=True, blank=True, default='')
    rank_3 = models.IntegerField(null=True, blank=True, default=0)
    actor = models.TextField(max_length=30, null=True, blank=True, default='')
    aspectRatio = models.FloatField(null=True, blank=True, default=0)
    audienceRating = models.FloatField(null=True, blank=True, default=0)
    author = models.TextField(max_length=30, null=True, blank=True, default='')
    backFinding = models.TextField(max_length=100, null=True, blank=True, default='')
    bandMaterialType = models.TextField(max_length=100, null=True, blank=True, default='')
    blurayRegion = models.TextField(max_length=100, null=True, blank=True, default='')
    ceroAgeRating = models.FloatField(null=True, blank=True, default=0)
    chainType = models.TextField(max_length=30, null=True, blank=True, default='')
    claspType = models.TextField(max_length=30, null=True, blank=True, default='')
    cpuManufacturer = models.TextField(max_length=50, null=True, blank=True, default='')
    cpuSpeed_value = models.FloatField(null=True, blank=True, default=0)
    cpuSpeed_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    cpuType = models.TextField(max_length=30, null=True, blank=True, default='')
    creator_value = models.FloatField(null=True, blank=True, default=0)
    creator_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    director = models.TextField(max_length=30, null=True, blank=True, default='')
    displaySize_value = models.FloatField(null=True, blank=True, default=0)
    displaySize_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    edition = models.TextField(max_length=50, null=True, blank=True, default='')
    episodeSequence = models.TextField(max_length=50, null=True, blank=True, default='')
    esrbAgeRating = models.FloatField(null=True, blank=True, default=0)
    feature = models.TextField(max_length=50, null=True, blank=True, default='')  # 特徴
    flavor = models.TextField(max_length=50, null=True, blank=True, default='')  # フレーバー
    format_val = models.TextField(max_length=50, null=True, blank=True, default='')
    gemType = models.TextField(max_length=30, null=True, blank=True, default='')
    genre = models.TextField(max_length=30, null=True, blank=True, default='')
    golfClubFlex = models.TextField(max_length=30, null=True, blank=True, default='')
    golfClubLoft_value = models.FloatField(null=True, blank=True, default=0)
    golfClubLoft_unit = models.TextField(max_length=50, null=True, blank=True, default='')
    handOrientation = models.TextField(max_length=50, null=True, blank=True, default='')
    hardDiskInterface = models.TextField(max_length=50, null=True, blank=True, default='')
    hardDiskSize_value = models.FloatField(null=True, blank=True, default=0)
    hardDiskSize_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    hardwarePlatform = models.TextField(max_length=50, null=True, blank=True, default='')
    hazardousMaterialType = models.TextField(max_length=50, null=True, blank=True, default='')
    isAutographed = models.BooleanField(null=True, blank=True, default=False)
    isEligibleForTradeIn = models.BooleanField(null=True, blank=True, default=False)
    isMemorabilia = models.BooleanField(null=True, blank=True, default=False)
    issuesPerYear = models.TextField(max_length=10, null=True, blank=True, default='')
    itemPartNumber = models.FloatField(null=True, blank=True, default=0)
    languages = models.TextField(max_length=30, null=True, blank=True, default='')
    legalDisclaimer = models.TextField(max_length=30, null=True, blank=True, default='')
    manufacturerMaximumAge_value = models.FloatField(null=True, blank=True, default=0)
    manufacturerMaximumAge_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    manufacturerMinimumAge_value = models.FloatField(null=True, blank=True, default=0)
    manufacturerMinimumAge_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    manufacturerPartsWarrantyDescription = models.TextField(max_length=300, null=True, blank=True, default='')
    materialType = models.TextField(max_length=30, null=True, blank=True, default='')
    maximumResolution_value = models.FloatField(null=True, blank=True, default=0)
    maximumResolution_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    mediaType = models.TextField(max_length=50, null=True, blank=True, default='')
    metalStamp = models.TextField(max_length=50, null=True, blank=True, default='')
    metalType = models.TextField(max_length=50, null=True, blank=True, default='')
    model = models.TextField(max_length=100, null=True, blank=True, default='')  # モデル
    numberOfDiscs = models.IntegerField(null=True, blank=True, default=0)
    numberOfIssues = models.IntegerField(null=True, blank=True, default=0)
    numberOfItems = models.IntegerField(null=True, blank=True, default=0)
    numberOfPages = models.IntegerField(null=True, blank=True, default=0)
    numberOfTracks = models.IntegerField(null=True, blank=True, default=0)
    operatingSystem = models.TextField(max_length=100, null=True, blank=True, default='')
    opticalZoom_value = models.FloatField(null=True, blank=True, default=0)
    opticalZoom_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    pegiRating = models.FloatField(null=True, blank=True, default=0)
    processorCount = models.IntegerField(null=True, blank=True, default=0)
    productTypeSubcategory = models.TextField(max_length=50, null=True, blank=True, default='')
    publicationDate = models.TextField(max_length=20, null=True, blank=True, default='')
    regionCode = models.TextField(max_length=20, null=True, blank=True, default='')
    ringSize = models.TextField(max_length=20, null=True, blank=True, default='')
    runningTime_value = models.FloatField(null=True, blank=True, default=0)
    runningTime_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    shaftMaterial = models.TextField(max_length=50, null=True, blank=True, default='')
    scent = models.TextField(max_length=50, null=True, blank=True, default='')
    seasonSequence = models.TextField(max_length=50, null=True, blank=True, default='')
    seikodoProductCode = models.TextField(max_length=50, null=True, blank=True, default='')
    sizePerPearl = models.TextField(max_length=50, null=True, blank=True, default='')

    label = models.TextField(max_length=100, null=True, blank=True, default='')
    list_price_amount = models.FloatField(null=True, blank=True, default=0)
    list_price_currency_code = models.TextField(max_length=50, null=True, blank=True, default='')
    list_price_code = models.TextField(max_length=50, null=True, blank=True, default='')
    manufacturer = models.TextField(max_length=100, null=True, blank=True, default='')
    package_quantity = models.FloatField(null=True, blank=True, default=0)
    part_number = models.TextField(max_length=100, null=True, blank=True, default='')
    platform = models.TextField(max_length=100, null=True, blank=True, default='')
    product_group = models.TextField(max_length=100, null=True, blank=True, default='')
    product_type_name = models.TextField(max_length=100, null=True, blank=True, default='')
    release_date = models.TextField(max_length=20, null=True, blank=True, default='')
    publisher = models.TextField(max_length=100, null=True, blank=True, default='')
    size = models.TextField(max_length=100, null=True, blank=True, default='')  # サイズ
    small_image_url = models.TextField(max_length=300, null=True, blank=True, default='')
    small_image_height_value = models.FloatField(null=True, blank=True, default=0)
    small_image_height_units = models.TextField(max_length=30, null=True, blank=True, default='')
    small_image_width_value = models.FloatField(null=True, blank=True, default=0)
    small_image_width_units = models.TextField(max_length=30, null=True, blank=True, default='')
    subscriptionLength_value = models.FloatField(null=True, blank=True, default=0)
    subscriptionLength_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    systemMemorySize_value = models.FloatField(null=True, blank=True, default=0)
    systemMemorySize_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    systemMemoryType = models.TextField(max_length=50, null=True, blank=True, default='')
    theatricalReleaseDate = models.TextField(max_length=30, null=True, blank=True, default='')
    totalDiamondWeight_value = models.FloatField(null=True, blank=True, default=0)
    totalDiamondWeight_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    totalGemWeight_value = models.FloatField(null=True, blank=True, default=0)
    totalGemWeight_unit = models.TextField(max_length=30, null=True, blank=True, default='')
    warranty = models.TextField(max_length=30, null=True, blank=True, default='')
    weeeTaxValue_amount = models.FloatField(null=True, blank=True, default=0)
    weeeTaxValue_currency_code = models.TextField(max_length=30, null=True, blank=True, default='')

    studio = models.TextField(max_length=100, null=True, blank=True, default='')
    relationships_asin_1 = models.TextField(max_length=12, null=True, default='', blank=True)
    sales_rankings_cat_id = models.TextField(max_length=100, null=True, blank=True, default='')
    p_cat_id_0 = models.BigIntegerField(null=True, blank=True, default=0)  # カテゴリID
    p_cat_id_1 = models.BigIntegerField(null=True, blank=True, default=0)  # カテゴリID_1
    p_cat_id_2 = models.BigIntegerField(null=True, blank=True, default=0)  # カテゴリID_2
    p_cat_name_0 = models.TextField(max_length=330, null=True, blank=True, default='')  # カテゴリ名
    p_cat_name_1 = models.TextField(max_length=330, null=True, blank=True, default='')  # カテゴリ名_1
    p_cat_name_2 = models.TextField(max_length=330, null=True, blank=True, default='')  # カテゴリ名_2

    buybox_listing_price = models.FloatField(null=True, blank=True, default=0)  # カート価格
    buybox_currency_cd = models.TextField(max_length=12, null=True, default='', blank=True)  # カート通貨コード
    buybox_condition = models.TextField(max_length=12, null=True, default='', blank=True)  # カート出品状態
    buybox_shipping_price = models.FloatField(null=True, blank=True, default=0)  # カート送料
    buybox_quantitytier = models.IntegerField(null=True, blank=True, default=0)  # カートの在庫数
    shipfrom_country = models.TextField(max_length=10, null=True, default='', blank=True)  # 出品者の所在国
    num_offers_amazon = models.FloatField(null=True, blank=True, default=0)  # NumberOfOffersのamazon出品者数
    num_offers_merchant = models.FloatField(null=True, blank=True, default=0)  # NumberOfOffersのMerchant出品者数
    ok_seller_feedback_rate = models.FloatField(null=True, blank=True, default=0)  # OKと判断されたセラーのfeedback rate
    ok_seller_id = models.TextField(max_length=20, null=True, default='', blank=True)  # OKと判断されたセラーのid
    is_seller_ok = models.BooleanField(null=True, blank=True, default=False)  # 出品OKかどうかの出品者状態による判定　False:NG判定 True:OK
    shipping_size = models.IntegerField(null=True, blank=True, default=0)  # 送料区分

    # スクレイピングの結果
    product_title = models.TextField(max_length=200, null=True, default='', blank=True)  # タイトル
    description = models.TextField(max_length=400, null=True, default='', blank=True)  # description

    # 商品の詳細 productOverview_feature_div
    # 旧: p_o_f_0 .. p_o_f_9 (TextField)
    p_o_f = models.JSONField(
        null=True, blank=True, default=list,
        help_text="productOverview_feature_div; リスト[str]（旧: p_o_f_0..9）"
    )

    # 商品特徴 feature-bullets
    # 旧: f_b_0 .. f_b_9 (TextField)
    feature_bullets = models.JSONField(
        null=True, blank=True, default=list,
        help_text="feature-bullets; リスト[str]（旧: f_b_0..9）"
    )

    # 画面下部_詳細情報 productDetails_techSpec_section_1
    # 旧: p_d_t_s_th_0..9 / p_d_t_s_td_0..9 (TextField)
    techspec_th = models.JSONField(
        null=True, blank=True, default=list,
        help_text="techSpec th; リスト[str]（旧: p_d_t_s_th_0..9）"
    )
    techspec_td = models.JSONField(
        null=True, blank=True, default=list,
        help_text="techSpec td; リスト[str]（旧: p_d_t_s_td_0..9）"
    )

    # 画面下部_商品の説明 productDescription
    # 旧: p_d_0 .. p_d_9 (TextField)
    product_description = models.JSONField(
        null=True, blank=True, default=list,
        help_text="productDescription; リスト[str]（旧: p_d_0..9）"
    )

    # サムネイル画像 span[contains(@id,'a-autoid-') and contains(@id,'-announce')]/img/@src
    # 旧: img_tag_0 .. img_tag_19 (TextField)
    img_tags = models.JSONField(
        null=True, blank=True, default=list,
        help_text="サムネイル画像URL; リスト[str]（旧: img_tag_0..19）"
    )

    # 商品紹介コンテンツ
    # 旧: apm-sidemodule（img_a_s_m_0 / p_a_s_m_0）
    # 旧: aplus-module-wrapper（img_a_m_w_0..4 / p_a_m_w_0..4）
    # まとめて “1要素 = {img: str, text: str, kind: 'apm'|'aplus'}” として格納
    aplus_modules = models.JSONField(
        null=True, blank=True, default=list,
        help_text=(
            "商品紹介コンテンツ; リスト[{'img': str, 'text': str, 'kind': 'apm'|'aplus'}] "
            "(旧: img_a_s_m_0/p_a_s_m_0, img_a_m_w_0..4/p_a_m_w_0..4)"
        )
    )


    # blacklist関連の判定結果
    is_blacklist_ok = models.BooleanField(null=True, blank=True, default=False)  # ブラックリスト判定　False:NG判定 True:OK
    is_blacklist_ok_asin = models.BooleanField(null=True, blank=True, default=True)  # ASINの判定結果 False:NG判定 True:OK
    is_blacklist_ok_img = models.BooleanField(null=True, blank=True, default=True)  # 画像による判定結果 False:NG判定 True:OK
    is_blacklist_ok_keyword = models.BooleanField(null=True, blank=True, default=True)  # キーワードによる判定結果 False:NG判定 True:OK
    # キーワードによる判定結果を桁数によって保持しよう
    # デフォルト：10000000000　例えばタイトルとブランドがNGなら 00101 とする。
    # 末尾桁→タイトルの判定結果、NGなら１
    # 10の桁→商品説明の判定結果、NGなら１
    # 100の桁→ブランドの判定結果、NGなら１
    blacklist_keyword_flg = models.IntegerField(null=True, blank=True, default=0)

    # ※以下は古いY用の情報など。不要なら消してもいい
    # 取り込むショップのID
    shopid = models.TextField(max_length=50, null=True, blank=True, default='')
    gid = models.TextField(max_length=50, null=True, blank=True, default='')
    #gid = models.ForeignKey(YaItemList, to_field = 'gid', on_delete=models.CASCADE)
    # 管理用連番　CSVを取り込んだら＋１。処理バッチはこの連番で動く
    csv_no = models.IntegerField(null=True, blank=True, default=0)
    # Yahooのプロダクトカテゴリ
    y_cat_1 = models.TextField(max_length=100, null=True, blank=True, default='')
    y_cat_2 = models.TextField(max_length=100, null=True, blank=True, default='')
    # 自サイトのカテゴリ
    myshop_cat_all = models.TextField(max_length=300, null=True, blank=True, default='')
    myshop_cat_1 = models.TextField(max_length=100, null=True, blank=True, default='')
    myshop_cat_2 = models.TextField(max_length=100, null=True, blank=True, default='')

    # 卸業者の情報があればcsvから取り込む
    wholesale_price = models.FloatField(null=True, blank=True, default=0)
    wholesale_name = models.TextField(max_length=300, null=True, blank=True, default='')

    status = models.IntegerField(null=True, blank=True, default=0)  # 0:未処理 1:処理中 2:処理正常終了 3:異常終了
    create_date = models.DateTimeField(null=True, blank=True, default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)
    scraped_date = models.DateTimeField(null=True, blank=True)  # スクレイピングした時刻 ある程度経過したら取り直しとか

    def __str__(self):
        return str(self.asin)
        # return '<QooAsinDetail:asin=' + str(self.asin) + '>'


class QooAsinRelationDetail(models.Model):
    # Qoo10用ASINの関連商品（カラバリなど）に関わる情報を全て網羅してみる。
    # 親asinが存在するはず

    asin = models.CharField(max_length=12, default='', primary_key=True)
    parent_asin = models.ForeignKey(QooAsinDetail, on_delete=models.CASCADE)  # asinの親 QooAsinDetail）Foreign key
    marketplace_id = models.TextField(max_length=50, null=True, blank=True, default='')  # MarketplaceId
    seller_id = models.TextField(max_length=50, null=True, blank=True, default='')  #
    seller_sku = models.TextField(max_length=50, null=True, blank=True, default='')  #
    color = models.TextField(max_length=50, null=True, blank=True, default='')  #
    edition = models.TextField(max_length=50, null=True, blank=True, default='')  #
    flavor = models.TextField(max_length=50, null=True, blank=True, default='')  #
    gem_type = models.TextField(max_length=50, null=True, blank=True, default='')  #
    golf_club_flex = models.TextField(max_length=100, null=True, blank=True, default='')  #
    hand_orientation = models.TextField(max_length=100, null=True, blank=True, default='')  #
    hardware_platform = models.TextField(max_length=100, null=True, blank=True, default='')  #
    material_type_1 = models.TextField(max_length=100, null=True, blank=True, default='')  #
    material_type_2 = models.TextField(max_length=100, null=True, blank=True, default='')  #
    material_type_3 = models.TextField(max_length=100, null=True, blank=True, default='')  #
    metal_type = models.TextField(max_length=100, null=True, blank=True, default='')  #
    model = models.TextField(max_length=100, null=True, blank=True, default='')  #
    operating_system_1 = models.TextField(max_length=100, null=True, blank=True, default='')  #
    operating_system_2 = models.TextField(max_length=100, null=True, blank=True, default='')  #
    operating_system_3 = models.TextField(max_length=100, null=True, blank=True, default='')  #
    product_type_subcategory = models.TextField(max_length=200, null=True, blank=True, default='')  #
    ring_size = models.TextField(max_length=30, null=True, blank=True, default='')  #
    shaft_material = models.TextField(max_length=50, null=True, blank=True, default='')  #
    scent = models.TextField(max_length=100, null=True, blank=True, default='')  #
    size = models.TextField(max_length=110, null=True, blank=True, default='')  #
    size_per_pearl = models.TextField(max_length=30, null=True, blank=True, default='')  #
    golf_club_loft_value = models.TextField(max_length=30, null=True, blank=True, default='')  #
    golf_club_loft_units = models.TextField(max_length=30, null=True, blank=True, default='')  #
    total_diamond_weight_value = models.TextField(max_length=30, null=True, blank=True, default='')  #
    total_diamond_weight_units = models.TextField(max_length=30, null=True, blank=True, default='')  #
    total_gem_weight_value = models.TextField(max_length=30, null=True, blank=True, default='')  #
    total_gem_weight_units = models.TextField(max_length=30, null=True, blank=True, default='')  #
    package_quantity = models.IntegerField(null=True, blank=True, default=0)   #
    item_dimensions_height_value = models.TextField(max_length=30, null=True, blank=True, default='')  #
    item_dimensions_height_units = models.TextField(max_length=30, null=True, blank=True, default='')  #
    item_dimensions_length_value = models.TextField(max_length=30, null=True, blank=True, default='')  #
    item_dimensions_length_units = models.TextField(max_length=30, null=True, blank=True, default='')  #
    item_dimensions_width_value = models.TextField(max_length=30, null=True, blank=True, default='')  #
    item_dimensions_width_units = models.TextField(max_length=30, null=True, blank=True, default='')  #
    item_dimensions_weight_value = models.TextField(max_length=30, null=True, blank=True, default='')  #
    item_dimensions_weight_units = models.TextField(max_length=30, null=True, blank=True, default='')  #

    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)
    def __str__(self):
        return '<QooAsinRelationDetail:asin=' + str(self.asin) + '>'


class AsinBlacklistAsin(models.Model):
    # ASINのブラックリスト（asin）
    asin = models.CharField(max_length=12, default='', primary_key=True)
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)

class AsinBlacklistKeyword(models.Model):
    # ASINのブラックリスト（キーワード）
    keyword = models.TextField(max_length=100)
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)

class AsinBlacklistBrand(models.Model):
    # ASINのブラックリスト（ブランド）
    brand = models.TextField(max_length=100)
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)


class Friend(models.Model):
    name = models.CharField(max_length=100, \
                            validators=[alpha_only])
    mail = models.EmailField(max_length=200)
    gender = models.BooleanField()
    age = models.IntegerField()
    birthday = models.DateField()

    def __str__(self):
        return '<Friend:id=' + str(self.id) + ', ' + \
               self.name + '(' + str(self.age) + ')>'


class Message(models.Model):
    friend = models.ForeignKey(Friend, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    content = models.CharField(max_length=300)
    pub_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '<Message:id=' + str(self.id) + ', ' + \
               self.title + '(' + str(self.pub_date) + ')>'

    class Meta:
        ordering = ('pub_date',)

class YaShopImportAmaGoodsDetail(models.Model):
    asin = models.TextField(max_length=12, default='')
    title = models.TextField(max_length=300, default='')
    url = models.URLField(null=True, blank=True)
    amount = models.FloatField(null=True, blank=True, default=0)
    binding = models.TextField(max_length=200, null=True, blank=True, default='')
    brand = models.TextField(max_length=100, null=True, blank=True, default='')
    color = models.TextField(max_length=500, null=True, blank=True, default='')
    department = models.TextField(max_length=200, null=True, blank=True, default='')
    is_adlt = models.BooleanField(default=False)
    i_height = models.FloatField(null=True, blank=True, default=0)
    i_length = models.FloatField(null=True, blank=True, default=0)
    i_width = models.FloatField(null=True, blank=True, default=0)
    i_weight = models.FloatField(null=True, blank=True, default=0)
    p_height = models.FloatField(null=True, blank=True, default=0)
    p_length = models.FloatField(null=True, blank=True, default=0)
    p_width = models.FloatField(null=True, blank=True, default=0)
    p_weight = models.FloatField(null=True, blank=True, default=0)
    rank_cat_1 = models.TextField(max_length=100, null=True, blank=True, default='')
    rank_1 = models.IntegerField(null=True, blank=True, default=0)
    rank_cat_2 = models.TextField(max_length=100, null=True, blank=True, default='')
    rank_2 = models.IntegerField(null=True, blank=True, default=0)
    rank_cat_3 = models.TextField(max_length=100, null=True, blank=True, default='')
    rank_3 = models.IntegerField(null=True, blank=True, default=0)
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)
    # 取り込むショップのID
    shopid = models.TextField(max_length=50, null=True, blank=True, default='')
    gid = models.TextField(max_length=50, null=True, blank=True, default='')
    #gid = models.ForeignKey(YaItemList, to_field = 'gid', on_delete=models.CASCADE)
    # 管理用連番　CSVを取り込んだら＋１。処理バッチはこの連番で動く
    csv_no = models.IntegerField(null=True, blank=True, default=0)
    # Yahooのプロダクトカテゴリ
    y_cat_1 = models.TextField(max_length=100, null=True, blank=True, default='')
    y_cat_2 = models.TextField(max_length=100, null=True, blank=True, default='')
    # 自サイトのカテゴリ
    myshop_cat_all = models.TextField(max_length=300, null=True, blank=True, default='')
    myshop_cat_1 = models.TextField(max_length=100, null=True, blank=True, default='')
    myshop_cat_2 = models.TextField(max_length=100, null=True, blank=True, default='')

    def __str__(self):
        return '<YaShopImportAmaGoodsDetail:asin=' + str(self.asin) + ', ' + \
               'title[' + self.title + '] >'


class YaShopImportSpApiAmaGoodsDetail(models.Model):
    asin = models.TextField(max_length=12, default='')
    title = models.TextField(max_length=300, default='')
    url = models.URLField(null=True, blank=True)
    amount = models.FloatField(null=True, blank=True, default=0)
    binding = models.TextField(max_length=200, null=True, blank=True, default='')
    brand = models.TextField(max_length=100, null=True, blank=True, default='')
    color = models.TextField(max_length=500, null=True, blank=True, default='')
    department = models.TextField(max_length=200, null=True, blank=True, default='')
    is_adlt = models.BooleanField(default=False)
    i_height = models.FloatField(null=True, blank=True, default=0)
    i_length = models.FloatField(null=True, blank=True, default=0)
    i_width = models.FloatField(null=True, blank=True, default=0)
    i_weight = models.FloatField(null=True, blank=True, default=0)
    p_height = models.FloatField(null=True, blank=True, default=0)
    p_length = models.FloatField(null=True, blank=True, default=0)
    p_width = models.FloatField(null=True, blank=True, default=0)
    p_weight = models.FloatField(null=True, blank=True, default=0)
    rank_cat_1 = models.TextField(max_length=100, null=True, blank=True, default='')
    rank_1 = models.IntegerField(null=True, blank=True, default=0)
    rank_cat_2 = models.TextField(max_length=100, null=True, blank=True, default='')
    rank_2 = models.IntegerField(null=True, blank=True, default=0)
    rank_cat_3 = models.TextField(max_length=100, null=True, blank=True, default='')
    rank_3 = models.IntegerField(null=True, blank=True, default=0)
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)
    # 取り込むショップのID
    shopid = models.TextField(max_length=50, null=True, blank=True, default='')
    gid = models.TextField(max_length=50, null=True, blank=True, default='')
    #gid = models.ForeignKey(YaItemList, to_field = 'gid', on_delete=models.CASCADE)
    # 管理用連番　CSVを取り込んだら＋１。処理バッチはこの連番で動く
    csv_no = models.IntegerField(null=True, blank=True, default=0)
    # Yahooのプロダクトカテゴリ
    y_cat_1 = models.TextField(max_length=100, null=True, blank=True, default='')
    y_cat_2 = models.TextField(max_length=100, null=True, blank=True, default='')
    # 自サイトのカテゴリ
    myshop_cat_all = models.TextField(max_length=300, null=True, blank=True, default='')
    myshop_cat_1 = models.TextField(max_length=100, null=True, blank=True, default='')
    myshop_cat_2 = models.TextField(max_length=100, null=True, blank=True, default='')

    def __str__(self):
        return '<YaShopImportSpApiAmaGoodsDetail:asin=' + str(self.asin) + ', ' + \
               'title[' + self.title + '] >'


class AsinDetail(models.Model):
    # ASINによる情報を全て網羅してみる。

    asin = models.CharField(max_length=12, default='', primary_key=True)
    title = models.TextField(max_length=300, default='')
    url = models.URLField(null=True, blank=True)
    amount = models.FloatField(null=True, blank=True, default=0)
    binding = models.TextField(max_length=200, null=True, blank=True, default='')
    brand = models.TextField(max_length=100, null=True, blank=True, default='')
    color = models.TextField(max_length=500, null=True, blank=True, default='')
    department = models.TextField(max_length=200, null=True, blank=True, default='')
    is_adlt = models.BooleanField(default=False)
    i_height = models.FloatField(null=True, blank=True, default=0)
    i_length = models.FloatField(null=True, blank=True, default=0)
    i_width = models.FloatField(null=True, blank=True, default=0)
    i_weight = models.FloatField(null=True, blank=True, default=0)
    p_height = models.FloatField(null=True, blank=True, default=0)
    p_length = models.FloatField(null=True, blank=True, default=0)
    p_width = models.FloatField(null=True, blank=True, default=0)
    p_weight = models.FloatField(null=True, blank=True, default=0)
    rank_cat_1 = models.TextField(max_length=100, null=True, blank=True, default='')
    rank_1 = models.IntegerField(null=True, blank=True, default=0)
    rank_cat_2 = models.TextField(max_length=100, null=True, blank=True, default='')
    rank_2 = models.IntegerField(null=True, blank=True, default=0)
    rank_cat_3 = models.TextField(max_length=100, null=True, blank=True, default='')
    rank_3 = models.IntegerField(null=True, blank=True, default=0)

    label = models.TextField(max_length=100, null=True, blank=True, default='')
    list_price_amount = models.FloatField(null=True, blank=True, default=0)
    list_price_currency_code = models.TextField(max_length=50, null=True, blank=True, default='')
    manufacturer = models.TextField(max_length=100, null=True, blank=True, default='')
    package_quantity = models.FloatField(null=True, blank=True, default=0)
    part_number = models.TextField(max_length=100, null=True, blank=True, default='')
    product_group = models.TextField(max_length=100, null=True, blank=True, default='')
    product_type_name = models.TextField(max_length=100, null=True, blank=True, default='')
    publisher = models.TextField(max_length=100, null=True, blank=True, default='')
    size = models.TextField(max_length=100, null=True, blank=True, default='')
    small_image_url = models.TextField(max_length=300, null=True, blank=True, default='')
    studio = models.TextField(max_length=100, null=True, blank=True, default='')
    relationships_asin_1 = models.TextField(max_length=12, default='', blank=True)
    sales_rankings_cat_id = models.TextField(max_length=100, null=True, blank=True, default='')
    product_category_id = models.FloatField(null=True, blank=True, default=0)
    product_category_rank = models.FloatField(null=True, blank=True, default=0)

    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)
    # 取り込むショップのID
    shopid = models.TextField(max_length=50, null=True, blank=True, default='')
    gid = models.TextField(max_length=50, null=True, blank=True, default='')
    #gid = models.ForeignKey(YaItemList, to_field = 'gid', on_delete=models.CASCADE)
    # 管理用連番　CSVを取り込んだら＋１。処理バッチはこの連番で動く
    csv_no = models.IntegerField(null=True, blank=True, default=0)
    # Yahooのプロダクトカテゴリ
    y_cat_1 = models.TextField(max_length=100, null=True, blank=True, default='')
    y_cat_2 = models.TextField(max_length=100, null=True, blank=True, default='')
    # 自サイトのカテゴリ
    myshop_cat_all = models.TextField(max_length=300, null=True, blank=True, default='')
    myshop_cat_1 = models.TextField(max_length=100, null=True, blank=True, default='')
    myshop_cat_2 = models.TextField(max_length=100, null=True, blank=True, default='')

    # 卸業者の情報があればcsvから取り込む
    wholesale_price = models.FloatField(null=True, blank=True, default=0)
    wholesale_name = models.TextField(max_length=300, null=True, blank=True, default='')

    status = models.IntegerField(default=0) # 0:未処理 1:処理中 2:処理正常終了 3:異常終了
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)

    def __str__(self):
        return '<AsinDetail:asin=' + str(self.asin) + '>'


class WowmaGoodsDetail(models.Model):
    id = models.BigAutoField('ID', primary_key=True)  # id
    gid = models.CharField('商品ID', max_length=30, null=True, blank=True) # BA111 + 数字15桁(idを元に0埋めしよう)
    gcode = models.TextField('管理用商品名', max_length=30, default='',null=True, blank=True)
    asin = models.ForeignKey(QooAsinDetail, verbose_name='asin', on_delete=models.DO_NOTHING)
    WOW_UPD_STATUS = ((0, '未登録'), (1, '掲載中'), (2, '登録済みだが未掲載'))
    wow_upd_status = models.IntegerField('wow掲載状況', choices=WOW_UPD_STATUS, default=0, null=True, blank=True) # wowmaの掲載ステータス
    WOW_STATUS = ((0, '確認待ち'), (1, 'OK'), (2, 'NG'), (3, '在庫切れ'))
    wow_on_flg = models.IntegerField('wowステータス', choices=WOW_STATUS, default=0, null=True, blank=True)  # wowmaの出品ステータス　NG はブラックリスト
    wow_ng_flg = models.BooleanField('wow出品NGフラグ', null=True, blank=True, default=False)  # 出品NG False:出品Ok / True: 出品NG
    wow_gname = models.TextField('wowma商品名', max_length=300, default='', null=True, blank=True)  # wowmaの商品名
    wow_gdetail = models.TextField('wowma商品詳細', max_length=1024, default='', null=True, blank=True) # wowmaの商品詳細
    wow_descriptionForSP = models.TextField('wowma SP用商品説明', max_length=10240, default='', null=True, blank=True) # wowmaのSP用商品説明
    wow_descriptionForPC = models.TextField('wowma PC用商品説明', max_length=10240, default='', null=True, blank=True) # wowmaのPC用商品説明
    wow_detailDescription = models.TextField('wowma 商品詳細説明', max_length=640, default='', null=True, blank=True) # wowmaの商品詳細説明
    wow_lotnum = models.IntegerField('wowmaロットナンバー', default=0, null=True, blank=True)  # wowmaロットナンバー
    wow_keyword = models.TextField('wowma検索キーワード', max_length=350, default='', null=True, blank=True) # wowmaの検索ワード 20文字 x 3個まで設定可能(ex: シャツ、デニムシャツ、デニムのシャツ)Max 10 keywords, a keyword: Max 30　
    wow_worn_key = models.TextField('wowma要注意キーワード', max_length=200, default='', null=True, blank=True) # wowmaの商品詳細に含まれる危険ワード
    wow_price = models.IntegerField('wowma価格', default=0, null=True, blank=True) # wowmaの価格
    wow_fixed_price = models.IntegerField('wowma固定価格', default=0, null=True, blank=True) # wowmaの固定価格。もしこれが0より大きければ優先される
    wow_postage_segment = models.IntegerField('送料設定区分', default=2, null=True, blank=True)  # wowmaの# 送料設定区分 1:送料別/2:送料込み/3:個別送料
    wow_postage = models.IntegerField('個別送料', default=0, null=True, blank=True)  # wowmaの個別送料
    wow_delivery_method_id = models.IntegerField('配送方法ID', default=0, null=True, blank=True)  # wowmaの配送方法ID
    ama_ctid = models.BigIntegerField('ama_cat_ID', default=0, null=True, blank=True)  # Amazonの紐づけ元カテゴリID
    wow_ctid = models.BigIntegerField('wow_cat_D', default=0, null=True, blank=True)  # wowmaのカテゴリID
    wow_tagid = models.TextField('タグID', default='', null=True, blank=True)  # wowmaの検索タグID　20文字 x 64個まで指定可能 半角スペース区切りで保持する
    stock = models.IntegerField('在庫数', default=0, null=True, blank=True)  # Amaから取得する在庫数
    wow_hinmei = models.TextField('品名', default='', null=True, blank=True)  # ロジスピの商品登録に使う品名をwow_ctidからセットする

    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)

    def __str__(self):
        return '<WowmaGoodsDetail:asin=' + str(self.asin.asin)


class WowmaSpecDetail(models.Model):
    # wowma商品毎のスペック情報。親は WowmaGoodsDetail
    wow_goods_detail = models.ForeignKey(WowmaGoodsDetail, verbose_name='wow_goods_detail', on_delete=models.CASCADE)
    spec_title_0 = models.TextField('スペックタイトル0', max_length=20, default='', null=True, blank=True)  # スペックタイトル
    spec_title_1 = models.TextField('スペックタイトル1', max_length=20, default='', null=True, blank=True)  # スペックタイトル
    spec_title_2 = models.TextField('スペックタイトル2', max_length=20, default='', null=True, blank=True)  # スペックタイトル
    spec_title_3 = models.TextField('スペックタイトル3', max_length=20, default='', null=True, blank=True)  # スペックタイトル
    spec_title_4 = models.TextField('スペックタイトル4', max_length=20, default='', null=True, blank=True)  # スペックタイトル
    d_spec_name_0 = models.TextField('スペック名0', max_length=20, default='', null=True, blank=True)  # スペック名
    d_spec_name_1 = models.TextField('スペック名1', max_length=20, default='', null=True, blank=True)  # スペック名
    d_spec_name_2 = models.TextField('スペック名2', max_length=20, default='', null=True, blank=True)  # スペック名
    d_spec_name_3 = models.TextField('スペック名3', max_length=20, default='', null=True, blank=True)  # スペック名
    d_spec_name_4 = models.TextField('スペック名4', max_length=20, default='', null=True, blank=True)  # スペック名
    d_spec_0 = models.TextField('スペック値0', max_length=20, default='', null=True, blank=True)  # スペック値
    d_spec_1 = models.TextField('スペック値1', max_length=20, default='', null=True, blank=True)  # スペック値
    d_spec_2 = models.TextField('スペック値2', max_length=20, default='', null=True, blank=True)  # スペック値
    d_spec_3 = models.TextField('スペック値3', max_length=20, default='', null=True, blank=True)  # スペック値
    d_spec_4 = models.TextField('スペック値4', max_length=20, default='', null=True, blank=True)  # スペック値
    d_spec_seq_0 = models.TextField('スペック項目順序0', max_length=20, default='', null=True, blank=True)  # スペック項目順序
    d_spec_seq_1 = models.TextField('スペック項目順序1', max_length=20, default='', null=True, blank=True)  # スペック項目順序
    d_spec_seq_2 = models.TextField('スペック項目順序2', max_length=20, default='', null=True, blank=True)  # スペック項目順序
    d_spec_seq_3 = models.TextField('スペック項目順序3', max_length=20, default='', null=True, blank=True)  # スペック項目順序
    d_spec_seq_4 = models.TextField('スペック項目順序4', max_length=20, default='', null=True, blank=True)  # スペック項目順序

    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)

    def __str__(self):
        return '<WowmaSpecDetail:asin=' + str(self.wow_goods_detail)


class WowCategory(models.Model):
    # wowmaのカテゴリ一覧
    # wowmaは第４階層まで
    product_cat_id = models.IntegerField(primary_key=True)
    product_cat_name = models.TextField(max_length=500, null=True, blank=True, default='')  # カテゴリフルパス
    level_1_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第1階層 カテゴリ名
    level_2_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第2階層 カテゴリ名
    level_3_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第3階層 カテゴリ名
    level_4_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第4階層 カテゴリ名
    ama_level_1_cat_id = models.BigIntegerField(null=True, blank=True, default=0)  # 第1階層 ama_caid
    ama_level_2_cat_id = models.BigIntegerField(null=True, blank=True, default=0)  # 第2階層 ama_caid
    ama_level_3_cat_id = models.BigIntegerField(null=True, blank=True, default=0)  # 第3階層 ama_caid
    ama_level_1_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第1階層 ama_カテゴリ名
    ama_level_2_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第2階層 ama_カテゴリ名
    ama_level_3_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第3階層 ama_カテゴリ名
    # ama_cat = models.ManyToManyField(AmaCategory)
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)


class QooCategory(models.Model):
    # Qoo10のカテゴリ一覧
    """ 形式は以下　小分類がユニークなのでprimaryに。
    大分類カテゴリーコード	大分類カテゴリー	中分類カテゴリーコード	中分類カテゴリー	小分類カテゴリーコード	小分類カテゴリー
    100000001	レディース服	200000001	スーツ	300002246	パンツスーツ
    """
    s_cat_id = models.IntegerField(primary_key=True)  # 小分類カテゴリコード
    s_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')
    m_cat_id = models.IntegerField(null=True, blank=True, default=0)  # 中分類カテゴリコード
    m_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')
    l_cat_id = models.IntegerField(null=True, blank=True, default=0)  # 大分類カテゴリコード
    l_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)

    def __str__(self):
        return '<QooCategory:s_cat_id=' + str(self.s_cat_id) + '>'


class AmaCategory(models.Model):
    # Amazonのカテゴリ一覧 SP-API から取れそう
    # https://github.com/amzn/selling-partner-api-docs/blob/a33be7199c935c1c01366f3cad69e36f00f4a12b/references/catalog-items-api/catalogItemsV0.md#listcatalogcategoriesresponse
    # ListOfCategories > Categories
    # 取り出すAPIはこれ
    # https://github.com/amzn/selling-partner-api-docs/blob/a33be7199c935c1c01366f3cad69e36f00f4a12b/references/catalog-items-api/catalogItemsV0.md#listcatalogcategories
    # GET / catalog / v0 / categories
    # Operation: listCatalogCategories
    # これは指定したASINに対して親カテゴリを返す
    # 指定されたASINまたはSellerSKUに基づいて、商品が属する親カテゴリーを返します。

    # 第1/2階層は、カテゴリ名を / で分割して設定。
    # 他モールと紐づけるには
    # 1⃣ まず他モールの第一階層と、amaの第一階層を紐づけ
    # 2⃣ 他モールの第２階層と、amaの第２階層を紐づけ　→　これは大変そう
    # 3⃣ 第三階層以下は、上記２つ同士で絞り込んだ結果から、キーワードマッチでどれか当てはめていく
    #    最終的に自分の wow_cat_id が紐づくと。
    product_cat_id = models.BigIntegerField(primary_key=True)
    product_cat_name = models.TextField(max_length=500, null=True, blank=True, default='')
    parent_cat_id = models.BigIntegerField(null=True, blank=True, default=0)  # 親caid
    level_1_cat_id = models.BigIntegerField(null=True, blank=True, default=0)  # 第1階層 caid
    level_2_cat_id = models.BigIntegerField(null=True, blank=True, default=0)  # 第2階層 caid
    level_3_cat_id = models.BigIntegerField(null=True, blank=True, default=0)  # 第3階層 caid
    level_4_cat_id = models.BigIntegerField(null=True, blank=True, default=0)  # 第4階層 caid
    level_5_cat_id = models.BigIntegerField(null=True, blank=True, default=0)  # 第5階層 caid
    level_6_cat_id = models.BigIntegerField(null=True, blank=True, default=0)  # 第6階層 caid
    level_7_cat_id = models.BigIntegerField(null=True, blank=True, default=0)  # 第7階層 caid
    level_8_cat_id = models.BigIntegerField(null=True, blank=True, default=0)  # 第8階層 caid
    level_1_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第1階層 カテゴリ名
    level_2_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第2階層 カテゴリ名
    level_3_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第3階層 カテゴリ名
    level_4_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第4階層 カテゴリ名
    level_5_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第5階層 カテゴリ名
    level_6_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第6階層 カテゴリ名
    level_7_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第7階層 カテゴリ名
    level_8_cat_name = models.TextField(max_length=100, null=True, blank=True, default='')  # 第8階層 カテゴリ名
    qoo_cat_id = models.IntegerField(null=True, blank=True, default=0)
    wow_cat_id = models.IntegerField(null=True, blank=True, default=0)
    yahoo_cat_id = models.IntegerField(null=True, blank=True, default=0)
    qoo_cat = models.ManyToManyField(QooCategory, related_name='qoo_cat')
    wow_cat = models.ManyToManyField(WowCategory, related_name='wow_cat')
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(null=True, blank=True, auto_now=True)

    def __str__(self):
        return '<AmaCategory:product_cat_id=' + str(self.product_cat_id) + '>'
