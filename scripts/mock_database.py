import os
import sys
import pymysql

# 确保能 import 到根目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from text_to_sql.config import settings

def create_connection():
    return pymysql.connect(
        host=settings.MYSQL_HOST,
        port=int(settings.MYSQL_PORT),
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DB,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

DDL_STATEMENTS = [
    # 场景 1: 电商交易 (E-commerce)
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '用户唯一标识',
        username VARCHAR(50) NOT NULL COMMENT '用户登录名',
        email VARCHAR(100) COMMENT '用户电子邮箱',
        phone VARCHAR(20) COMMENT '用户手机号码',
        register_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
        status TINYINT DEFAULT 1 COMMENT '账户状态：1正常，0禁用'
    ) COMMENT='电商系统用户表';
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
        product_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '商品唯一标识',
        product_name VARCHAR(100) NOT NULL COMMENT '商品名称',
        category_id INT COMMENT '商品分类ID',
        price DECIMAL(10,2) NOT NULL COMMENT '商品当前售价',
        stock INT DEFAULT 0 COMMENT '当前库存数量',
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上架时间'
    ) COMMENT='商品信息表';
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        order_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '订单唯一标识',
        user_id BIGINT NOT NULL COMMENT '下单用户ID，关联users表',
        total_amount DECIMAL(10,2) NOT NULL COMMENT '订单总金额',
        order_status VARCHAR(20) DEFAULT 'PENDING' COMMENT '订单状态: PENDING, PAID, SHIPPED, COMPLETED, CANCELLED',
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '订单创建时间',
        pay_time DATETIME COMMENT '订单支付时间',
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    ) COMMENT='用户订单主表';
    """,
    """
    CREATE TABLE IF NOT EXISTS order_items (
        item_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '订单明细唯一标识',
        order_id BIGINT NOT NULL COMMENT '所属订单ID，关联orders表',
        product_id BIGINT NOT NULL COMMENT '购买商品ID，关联products表',
        quantity INT NOT NULL COMMENT '购买数量',
        unit_price DECIMAL(10,2) NOT NULL COMMENT '购买时商品单价',
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    ) COMMENT='订单明细表，记录订单中包含的具体商品及数量';
    """,
    """
    CREATE TABLE IF NOT EXISTS user_addresses (
        address_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '地址唯一标识',
        user_id BIGINT NOT NULL COMMENT '所属用户ID',
        province VARCHAR(50) NOT NULL COMMENT '省份',
        city VARCHAR(50) NOT NULL COMMENT '城市',
        district VARCHAR(50) NOT NULL COMMENT '区县',
        detail_address VARCHAR(200) NOT NULL COMMENT '详细街道门牌号',
        is_default TINYINT DEFAULT 0 COMMENT '是否为默认地址',
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    ) COMMENT='用户收货地址表';
    """,
    """
    CREATE TABLE IF NOT EXISTS shopping_cart (
        cart_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '购物车记录唯一标识',
        user_id BIGINT NOT NULL COMMENT '所属用户ID',
        product_id BIGINT NOT NULL COMMENT '加入购物车的商品ID',
        quantity INT NOT NULL DEFAULT 1 COMMENT '商品数量',
        add_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '加入购物车时间',
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    ) COMMENT='用户购物车记录表';
    """,
    """
    CREATE TABLE IF NOT EXISTS product_categories (
        category_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '分类唯一标识',
        category_name VARCHAR(50) NOT NULL COMMENT '分类名称',
        parent_id INT COMMENT '父分类ID，为0或null表示顶级分类'
    ) COMMENT='商品类目层级表';
    """,

    # 场景 2: 人力资源 (HR)
    """
    CREATE TABLE IF NOT EXISTS departments (
        dept_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '部门唯一标识',
        dept_name VARCHAR(100) NOT NULL COMMENT '部门名称',
        manager_id BIGINT COMMENT '部门负责人ID',
        location VARCHAR(100) COMMENT '部门所在办公地点'
    ) COMMENT='公司部门组织架构表';
    """,
    """
    CREATE TABLE IF NOT EXISTS employees (
        emp_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '员工唯一标识，工号',
        first_name VARCHAR(50) NOT NULL COMMENT '名字',
        last_name VARCHAR(50) NOT NULL COMMENT '姓氏',
        email VARCHAR(100) NOT NULL UNIQUE COMMENT '公司内部邮箱',
        phone_number VARCHAR(20) COMMENT '联系电话',
        hire_date DATE NOT NULL COMMENT '入职日期',
        job_title VARCHAR(50) NOT NULL COMMENT '岗位头衔',
        salary DECIMAL(12,2) NOT NULL COMMENT '当前基本薪资',
        dept_id INT COMMENT '所属部门ID',
        manager_id BIGINT COMMENT '直属上级领导ID',
        FOREIGN KEY (dept_id) REFERENCES departments(dept_id),
        FOREIGN KEY (manager_id) REFERENCES employees(emp_id)
    ) COMMENT='公司员工基本信息表';
    """,
    """
    CREATE TABLE IF NOT EXISTS attendance (
        record_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '打卡记录唯一标识',
        emp_id BIGINT NOT NULL COMMENT '员工ID',
        work_date DATE NOT NULL COMMENT '打卡日期',
        check_in_time TIME COMMENT '上班打卡时间',
        check_out_time TIME COMMENT '下班打卡时间',
        status VARCHAR(20) COMMENT '考勤状态: NORMAL, LATE, EARLY_LEAVE, ABSENT',
        FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
    ) COMMENT='员工每日考勤打卡记录表';
    """,
    """
    CREATE TABLE IF NOT EXISTS payroll (
        payroll_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '薪资发放记录唯一标识',
        emp_id BIGINT NOT NULL COMMENT '员工ID',
        pay_month VARCHAR(7) NOT NULL COMMENT '发薪月份，格式YYYY-MM',
        base_salary DECIMAL(12,2) NOT NULL COMMENT '当月基本工资',
        bonus DECIMAL(12,2) DEFAULT 0 COMMENT '当月奖金/绩效',
        deductions DECIMAL(12,2) DEFAULT 0 COMMENT '当月扣款(五险一金等)',
        net_pay DECIMAL(12,2) NOT NULL COMMENT '实际发放净薪资',
        pay_date DATE NOT NULL COMMENT '实际发薪日期',
        FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
    ) COMMENT='员工每月薪资发放流水表';
    """,
    """
    CREATE TABLE IF NOT EXISTS performance_reviews (
        review_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '绩效考核唯一标识',
        emp_id BIGINT NOT NULL COMMENT '被考核员工ID',
        reviewer_id BIGINT NOT NULL COMMENT '考核人(通常是直属领导)ID',
        review_period VARCHAR(20) NOT NULL COMMENT '考核周期，如 2023-Q1',
        score DECIMAL(4,2) NOT NULL COMMENT '绩效打分',
        rating VARCHAR(10) NOT NULL COMMENT '绩效等级，如 S, A, B, C',
        comments TEXT COMMENT '考核评价评语',
        FOREIGN KEY (emp_id) REFERENCES employees(emp_id),
        FOREIGN KEY (reviewer_id) REFERENCES employees(emp_id)
    ) COMMENT='员工定期绩效考核记录表';
    """,
    """
    CREATE TABLE IF NOT EXISTS job_history (
        history_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '调岗记录唯一标识',
        emp_id BIGINT NOT NULL COMMENT '员工ID',
        start_date DATE NOT NULL COMMENT '该岗位起始日期',
        end_date DATE COMMENT '该岗位结束日期，为空表示当前在职',
        job_title VARCHAR(50) NOT NULL COMMENT '当时的岗位头衔',
        dept_id INT NOT NULL COMMENT '当时的所属部门ID',
        FOREIGN KEY (emp_id) REFERENCES employees(emp_id),
        FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
    ) COMMENT='员工历史调岗与晋升记录表';
    """,

    # 场景 3: 仓储物流 (Logistics & Warehouse)
    """
    CREATE TABLE IF NOT EXISTS warehouses (
        warehouse_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '仓库唯一标识',
        warehouse_name VARCHAR(100) NOT NULL COMMENT '仓库名称',
        city VARCHAR(50) NOT NULL COMMENT '仓库所在城市',
        capacity INT NOT NULL COMMENT '仓库总容量(立方米或托盘数)',
        manager_name VARCHAR(50) COMMENT '仓库负责人姓名'
    ) COMMENT='物理仓库信息表';
    """,
    """
    CREATE TABLE IF NOT EXISTS inventory (
        inventory_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '库存记录唯一标识',
        warehouse_id INT NOT NULL COMMENT '所属仓库ID',
        product_id BIGINT NOT NULL COMMENT '商品ID，关联products表',
        quantity INT NOT NULL DEFAULT 0 COMMENT '当前可用库存数量',
        locked_quantity INT NOT NULL DEFAULT 0 COMMENT '已被订单锁定未发货的数量',
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
        UNIQUE KEY(warehouse_id, product_id),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    ) COMMENT='各仓库的具体商品库存分布表';
    """,
    """
    CREATE TABLE IF NOT EXISTS shipments (
        shipment_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '发货单唯一标识',
        order_id BIGINT NOT NULL COMMENT '关联的用户订单ID',
        warehouse_id INT NOT NULL COMMENT '发货出库的仓库ID',
        tracking_number VARCHAR(100) COMMENT '物流快递单号',
        carrier VARCHAR(50) COMMENT '承运物流公司名称',
        shipment_status VARCHAR(20) DEFAULT 'PREPARING' COMMENT '物流状态: PREPARING, SHIPPED, IN_TRANSIT, DELIVERED',
        shipped_date DATETIME COMMENT '实际出库发货时间',
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
    ) COMMENT='订单出库发货及物流追踪表';
    """,
    """
    CREATE TABLE IF NOT EXISTS inbound_receipts (
        receipt_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '入库单唯一标识',
        warehouse_id INT NOT NULL COMMENT '接收货物的仓库ID',
        supplier_name VARCHAR(100) COMMENT '供货商名称',
        receive_date DATETIME NOT NULL COMMENT '实际入库时间',
        operator_name VARCHAR(50) COMMENT '入库操作员姓名',
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
    ) COMMENT='仓库采购入库主单表';
    """,
    """
    CREATE TABLE IF NOT EXISTS inbound_items (
        item_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '入库明细唯一标识',
        receipt_id BIGINT NOT NULL COMMENT '所属入库单ID',
        product_id BIGINT NOT NULL COMMENT '入库商品ID',
        received_quantity INT NOT NULL COMMENT '实际清点入库数量',
        FOREIGN KEY (receipt_id) REFERENCES inbound_receipts(receipt_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    ) COMMENT='入库单具体的商品明细表';
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_transfers (
        transfer_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '调拨单唯一标识',
        from_warehouse_id INT NOT NULL COMMENT '调出仓库ID',
        to_warehouse_id INT NOT NULL COMMENT '调入仓库ID',
        product_id BIGINT NOT NULL COMMENT '调拨商品ID',
        quantity INT NOT NULL COMMENT '调拨数量',
        transfer_date DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '调拨发起时间',
        status VARCHAR(20) DEFAULT 'IN_TRANSIT' COMMENT '调拨状态: IN_TRANSIT, COMPLETED',
        FOREIGN KEY (from_warehouse_id) REFERENCES warehouses(warehouse_id),
        FOREIGN KEY (to_warehouse_id) REFERENCES warehouses(warehouse_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    ) COMMENT='跨仓库的商品库存调拨记录表';
    """,
    """
    CREATE TABLE IF NOT EXISTS suppliers (
        supplier_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '供应商唯一标识',
        supplier_name VARCHAR(100) NOT NULL COMMENT '供应商名称',
        contact_person VARCHAR(50) COMMENT '联系人姓名',
        contact_phone VARCHAR(20) COMMENT '联系人电话',
        address VARCHAR(200) COMMENT '供应商地址'
    ) COMMENT='商品采购供应商信息表';
    """
]

def main():
    print("开始连接数据库以注入测试数据...")
    try:
        connection = create_connection()
        with connection.cursor() as cursor:
            # 禁用外键检查，方便无序建表或重建
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            
            for ddl in DDL_STATEMENTS:
                print(f"正在执行建表语句:\n{ddl.strip().splitlines()[0]} ...")
                cursor.execute(ddl)
                
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        connection.commit()
        print("成功创建 20 张测试表！")
    except Exception as e:
        print(f"创建表时发生错误: {e}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

if __name__ == "__main__":
    main()
