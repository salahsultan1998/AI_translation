****Thing need to be improved versions: 1.0****
1. 数据库（云部署）:
    * 每个项目的数据库需要独立的
    * 用户可以通过界面看某个项目的的数据库，查询
    * 添加新的数据，需要确保原有的：没有重复，或冲突  
  
2. Batch size: 
    * 搞一个能自动设定batch size的逻辑，不用用户选。
    

3. 效率：
    * 能不能通过批量处理加快速度？（参考我之前搞得代码 asyinco？）
    
4. 其他：
    * excel 文档的列表名称。(用户可以自己选带翻译列表) 然后生成一个带source和target的新文档。
    * 不需要非得上产自己的excel，可以直接粘贴格子里，就是在线生成excel
    * 上传待翻译文档，也可以像上传数据库一样（自己选哪一列是text，保存也会在一个
    
  
**测试前准备：**
1. 检查目前DM03有没有遗漏或错误的地方，重新上传
2. 创建sawa项目，并上传相关数据库（tmx能不能转换成excel？）
3. 测试：DM0和sawa两个项目。（测试：上传好数据库后，需要做几份测试搞）
4. 完成部署

--- 
*** Vrsion 2 ***

1. allow the user to write some notes"备注"
2. fix the prompt: sometimes it makes it so short. 强化提示词
3. no need to upload excel every time "可以直接粘贴列表"


