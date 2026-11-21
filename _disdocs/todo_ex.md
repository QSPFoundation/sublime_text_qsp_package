В этом фрагменте почему-то не учитываются квадратные скобки

```qsp
# loc

if 0:

elseif $args[0]='em.arr.print':
	$result=$dyneval({
		$result = ''
		local a
		unpackarr 'a', [
			'нулевая ячейка', '   первая ячейка   ', ' вторая ячейка', '',
			[1,2,3,5,6],	'   пятая ячейка',	'',	'седьмая ячейка'
		]		

		$result = $str([
			@em.arr.print('$a'),
			@em.arr.print('$a','[only result]'),
			@em.arr.print('$a','[trim]'),
			@em.arr.print('$a','[trim] [only result]',[2,5],'|'),
			@em.arr.print('$a','[trim] [only result] [with last]',[2,5],'|')
		) & ! здесь не закрыта скобка
	})

elseif 34:
end
-- ;;d;d;d;d;d;
```

А в этом случае elseif и ниже уже подсвечиваются Invalid:

```qsp
# loc

if 0:

elseif $args[0]='em.arr.print':
	$result=$dyneval({
		$result = ''
		local a
		unpackarr 'a', [
			'нулевая ячейка', '   первая ячейка   ', ' вторая ячейка', '',
			[1,2,3,5,6],	'   пятая ячейка',	'',	'седьмая ячейка'
		]		

		$result = $str([
			@em.arr.print('$a'),
			@em.arr.print('$a','[only result]'),
			@em.arr.print('$a','[trim]'),
			
		) & ! здесь не закрыта скобка
	})

elseif 34:
end
-- ;;d;d;d;d;d;
```