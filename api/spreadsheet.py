class SpreadsheetService:
    def __init__(self, gc, url):
        self.gc = gc
        self.sh = self.gc.open_by_url(url)
        
    def add_record(self, wks_name, data):
        """
        新增使用者至試算表
        """
        wks = self.sh.worksheet_by_title(wks_name)
        wks.append_table(values=data)

    def get_column_index(self, wks, column_name):
        """Returns
        int: column_name 所在的 column index
        """
        return wks.get_row(1).index(column_name) + 1

    def get_worksheet_data(self, title: str):
        """
        Summary:
            取得工作表資料
        Args:
            title: 工作表名稱
        Returns:
            list: 工作表資料
        """
        wks = self.sh.worksheet_by_title(title)
        return wks.get_all_records()
    
    def update_cell_value(self, title: str, range: tuple, value: str):
        """
        Summary:
            更新工作表資料
        Args:
            title: 工作表名稱
            index: 要更新的列索引
            data: 要更新的資料
        """
        wks = self.sh.worksheet_by_title(title)
        wks.update_value(range, value)
    
    def delete_row(self, title: str, index: int):
        """
        Summary:
            刪除工作表資料
        Args:
            title: 工作表名稱
            index: 要刪除的列索引
        """
        wks = self.sh.worksheet_by_title(title)
        wks.delete_rows(index)