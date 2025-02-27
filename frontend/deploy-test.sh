
#!/bin/zsh
host=161.189.166.213
ssh www@$host << eeooff
rm -rf /data/www/ai_boke/dist
eeooff
echo delete_old_file

scp -r  ./dist/ www@$host:/data/www/ai_boke/dist
